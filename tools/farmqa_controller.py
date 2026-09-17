"""One persistent controller reservation queue. No Unity/computer execution."""
import argparse
from contextlib import closing
import hashlib
import hmac
import json
import math
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid


def checked_target(raw):
    target = json.loads(raw) if raw else None
    if not isinstance(target, dict):
        raise ValueError("A pinned event target is required")
    for key, limit in (("repository", 4096), ("requested_ref", 512), ("server_environment", 128)):
        value = target.get(key)
        if (not isinstance(value, str) or not value.strip() or len(value) > limit
                or any(ord(c) < 32 for c in value)):
            raise ValueError("Malformed pinned target")
    commit = target.get("commit_sha")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A full pinned commit is required")
    if (target.get("source") != "local_operator"
            or target.get("verification") != "not_verified_in_unity"):
        raise ValueError("Unknown target provenance")
    selected = target.get("selected_at")
    if isinstance(selected, bool) or not isinstance(selected, (int, float)) or not math.isfinite(selected):
        raise ValueError("Malformed target selection time")
    # Retain only target metadata, never arbitrary prompt/credential fields.
    return {key: target[key] for key in ("repository", "requested_ref", "commit_sha",
            "server_environment", "selected_at", "source", "verification")}


class ControllerStore:
    """Caller commits/rolls back and serializes its connection. No auto-reclaim.

    All mutations first take a SQLite write lock, including when the caller
    uses a deferred transaction. Separate processes must use this same ledger.
    The token is returned only to acquire's caller; status never exposes it.
    """
    def __init__(self, db):
        self.db = db
        db.execute("""CREATE TABLE IF NOT EXISTS controller_requests (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL UNIQUE, event_key TEXT NOT NULL UNIQUE,
            organization_id TEXT NOT NULL, session_id TEXT NOT NULL,
            source_ms REAL, target_json TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('queued','active','cancel_requested','cancelled','released')),
            owner TEXT, token_hash TEXT, created_at REAL NOT NULL,
            acquired_at REAL, released_at REAL,
            CHECK ((owner IS NULL) = (token_hash IS NULL)),
            CHECK (state NOT IN ('active','cancel_requested') OR token_hash IS NOT NULL))""")
        # This constant-expression index enforces one slot across every session.
        db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS controller_single_slot
            ON controller_requests((1)) WHERE state IN ('active','cancel_requested')""")

    def _write_lock(self):
        self.db.execute("UPDATE controller_requests SET state=state WHERE 0")
        if not self.db.in_transaction:
            raise ValueError("Controller mutations require an enclosing transaction")

    def enqueue(self, event_key):
        self._write_lock()
        old = self.db.execute("SELECT request_id FROM controller_requests WHERE event_key=?", (event_key,)).fetchone()
        if old:
            return old["request_id"]
        row = self.db.execute("""SELECT e.session_id,e.status,b.target_json,b.source_ms,b.stop_requested
            FROM events e JOIN bridge_jobs b USING(event_key) WHERE e.event_key=?""", (event_key,)).fetchone()
        parts = event_key.split(":")
        if not row or len(parts) != 3 or parts[1] not in ("created", "prompted"):
            raise ValueError("Unknown authenticated bridge event")
        org = parts[0]
        session = self.db.execute("""SELECT 1 FROM bridge_sessions
            WHERE organization_id=? AND session_id=?""", (org, row["session_id"])).fetchone()
        cutoff = self.db.execute("""SELECT max(cutoff_ms) FROM stop_requests
            WHERE session_id=? AND substr(stop_key,1,?)=?""",
            (row["session_id"], len(org)+1, org+":")).fetchone()[0]
        if (not session or row["stop_requested"] or row["status"] in ('cancelled', 'stop_pending', 'uncertain')
                or cutoff is not None and (row["source_ms"] is None or row["source_ms"] <= cutoff)):
            raise ValueError("Stopped or uncertain event cannot be queued")
        target = checked_target(row["target_json"])
        request_id = str(uuid.uuid4())
        self.db.execute("""INSERT INTO controller_requests
            (request_id,event_key,organization_id,session_id,source_ms,target_json,state,created_at)
            VALUES (?,?,?,?,?,?,'queued',?)""", (request_id,event_key,org,row["session_id"],
                    row["source_ms"],json.dumps(target),time.time()))
        return request_id

    def acquire(self, owner):
        if (not isinstance(owner, str) or not owner.strip() or len(owner) > 128
                or any(ord(c) < 32 for c in owner)):
            raise ValueError("A worker identifier is required")
        self._write_lock()
        if self.db.execute("SELECT 1 FROM controller_requests WHERE state IN ('active','cancel_requested')").fetchone():
            return None
        row = self.db.execute("SELECT * FROM controller_requests WHERE state='queued' ORDER BY sequence LIMIT 1").fetchone()
        if not row:
            return None
        token = secrets.token_urlsafe(32)
        self.db.execute("""UPDATE controller_requests SET state='active',owner=?,token_hash=?,acquired_at=?
            WHERE request_id=?""", (owner,hashlib.sha256(token.encode()).hexdigest(),time.time(),row["request_id"]))
        return {"request_id": row["request_id"], "event_key": row["event_key"],
                "organization_id": row["organization_id"], "session_id": row["session_id"],
                "target": json.loads(row["target_json"]), "token": token}

    def _owned(self, request_id, token):
        row = self.db.execute("SELECT * FROM controller_requests WHERE request_id=?", (request_id,)).fetchone()
        if (not row or not row["token_hash"] or not isinstance(token, str)
                or not hmac.compare_digest(row["token_hash"], hashlib.sha256(token.encode()).hexdigest())):
            raise ValueError("Controller reservation ownership mismatch")
        return row

    def cancelled(self, request_id, token):
        return self._owned(request_id, token)["state"] in ('cancel_requested', 'cancelled')

    def release(self, request_id, token):
        """Owner releases only after its work is quiescent. No force release."""
        self._write_lock()
        row = self._owned(request_id, token)
        if row["state"] in ('released', 'cancelled'):
            return row["state"]
        state = 'cancelled' if row["state"] == 'cancel_requested' else 'released'
        self.db.execute("UPDATE controller_requests SET state=?,released_at=? WHERE request_id=?",
                        (state,time.time(),request_id))
        return state

    def stop(self, organization_id, session_id, cutoff_ms):
        self._write_lock()
        self.db.execute("""UPDATE controller_requests SET
            released_at=CASE WHEN state='queued' THEN ? ELSE released_at END,
            state=CASE WHEN state='queued' THEN 'cancelled' ELSE 'cancel_requested' END
            WHERE organization_id=? AND session_id=? AND state IN ('queued','active')
            AND (source_ms IS NULL OR source_ms<=?)""", (time.time(),organization_id,session_id,cutoff_ms))

    def status(self):
        rows = self.db.execute("""SELECT request_id,event_key,organization_id,session_id,state,
            created_at,acquired_at,released_at,target_json FROM controller_requests ORDER BY sequence""")
        return [{**{k: row[k] for k in row.keys() if k != 'target_json'},
                 'target': json.loads(row['target_json'])} for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('enqueue', 'status'))
    parser.add_argument('--db', type=Path, default=Path(__file__).resolve().parents[1]/'.local/farmqa/events.sqlite3')
    parser.add_argument('--event')
    args = parser.parse_args()
    if args.command == 'enqueue' and not args.event:
        parser.error('enqueue requires --event with an existing bridge event key')
    mode = 'ro' if args.command == 'status' else 'rw'
    with closing(sqlite3.connect(args.db.resolve().as_uri()+'?mode='+mode, uri=True)) as db:
        db.row_factory = sqlite3.Row
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='controller_requests'").fetchone():
            raise ValueError('Receiver has not initialized the controller queue')
        # No schema writes in the read-only status path.
        store = ControllerStore.__new__(ControllerStore)
        store.db = db
        with db:
            request_id = store.enqueue(args.event) if args.command == 'enqueue' else None
        print(json.dumps({'request_id': request_id, 'execution_enabled': False,
                          'requests': store.status()}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error': type(exc).__name__}))
        raise SystemExit(1)
