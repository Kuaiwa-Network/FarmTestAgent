"""Durable conversation routing and pinned targets; no game execution."""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import uuid


def resolve_target(repository, ref, server_environment):
    """Read an existing local Git ref without fetching or changing the checkout."""
    if (not isinstance(ref, str) or not ref or ref.startswith("-")
            or len(ref) > 512 or any(c.isspace() for c in ref)):
        raise ValueError("Invalid Git ref")
    if not (ref.startswith("refs/") or re.fullmatch(r"[0-9a-fA-F]{40}", ref)):
        raise ValueError("Use a full refs/... name or a 40-character commit SHA")
    if (not isinstance(server_environment, str) or not server_environment.strip()
            or len(server_environment) > 128 or any(ord(c) < 32 for c in server_environment)):
        raise ValueError("Invalid server environment identifier")
    repository = Path(repository).resolve(strict=True)
    def git(*args):
        result = subprocess.run(["git", "-C", str(repository), *args],
                                capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise ValueError("Git target could not be resolved")
        return result.stdout.strip()
    root = Path(git("rev-parse", "--show-toplevel")).resolve(strict=True)
    commit = git("rev-parse", "--verify", "--end-of-options", ref + "^{commit}")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid resolved commit")
    return {"repository": str(root), "requested_ref": ref, "commit_sha": commit,
            "server_environment": server_environment, "selected_at": time.time(),
            "source": "local_operator", "verification": "not_verified_in_unity"}


class SessionStore:
    """Caller owns the SQLite transaction and the receiver's connection lock."""
    def __init__(self, db, organization_id):
        self.db = db
        self.org = organization_id
        db.execute("""CREATE TABLE IF NOT EXISTS bridge_sessions (
            organization_id TEXT NOT NULL, session_id TEXT NOT NULL,
            thread_id TEXT, state TEXT NOT NULL, binding_token TEXT NOT NULL UNIQUE,
            legacy INTEGER NOT NULL DEFAULT 0, client_thread_id TEXT, candidate_thread_id TEXT,
            next_check REAL NOT NULL DEFAULT 0, created_at REAL NOT NULL,
            error TEXT, target_json TEXT,
            PRIMARY KEY (organization_id,session_id))""")
        if "candidate_thread_id" not in {r[1] for r in db.execute("PRAGMA table_info(bridge_sessions)")}:
            db.execute("ALTER TABLE bridge_sessions ADD COLUMN candidate_thread_id TEXT")
        db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS isolated_session_thread
            ON bridge_sessions(thread_id) WHERE legacy=0 AND thread_id IS NOT NULL""")

    def get(self, session_id):
        return self.db.execute("""SELECT * FROM bridge_sessions
            WHERE organization_id=? AND session_id=?""", (self.org, session_id)).fetchone()

    def ensure(self, session_id, legacy_thread=None):
        self.db.execute("""INSERT OR IGNORE INTO bridge_sessions
            (organization_id,session_id,thread_id,state,binding_token,legacy,created_at)
            VALUES (?,?,?,?,?,?,?)""", (self.org, session_id, legacy_thread,
                "ready" if legacy_thread else "new", str(uuid.uuid4()),
                int(legacy_thread is not None), time.time()))
        return self.get(session_id)

    def bind(self, session_id, thread_id):
        row = self.get(session_id)
        if not row or row["state"] == "ready":
            raise ValueError("Session is missing or already bound")
        if not isinstance(thread_id, str) or not thread_id or len(thread_id) > 128:
            raise ValueError("Missing actual Codex task ID")
        if self.db.execute("SELECT 1 FROM bridge_sessions WHERE thread_id=?", (thread_id,)).fetchone():
            raise ValueError("Codex task already belongs to another session")
        self.db.execute("""UPDATE bridge_sessions SET thread_id=?,state='ready',error=NULL,
            next_check=0 WHERE organization_id=? AND session_id=?""", (thread_id, self.org, session_id))
        self.db.execute("""UPDATE bridge_jobs SET thread_id=?,next_check=0 WHERE thread_id=''
            AND event_key IN (SELECT event_key FROM events WHERE session_id=?
                AND substr(event_key,1,?)=?)""",
            (thread_id, session_id, len(self.org)+1, self.org+":"))

    def set_target(self, session_id, target):
        if self.get(session_id) is None:
            raise ValueError("Unknown Linear session")
        # Only future enqueues inherit this target. Existing job snapshots never change.
        self.db.execute("""UPDATE bridge_sessions SET target_json=?
            WHERE organization_id=? AND session_id=?""",
            (json.dumps(target) if target is not None else None, self.org, session_id))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("sessions", "set-target", "clear-target"))
    parser.add_argument("--db", type=Path,
                        default=Path(__file__).resolve().parents[1] / ".local/farmqa/events.sqlite3")
    parser.add_argument("--organization", required=True)
    parser.add_argument("--session")
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--ref")
    parser.add_argument("--server-environment")
    args = parser.parse_args()
    if args.command != "sessions" and not args.session:
        parser.error("A Linear --session is required")
    if args.command == "set-target" and not all((args.repository, args.ref, args.server_environment)):
        parser.error("set-target requires --repository, --ref, and --server-environment")
    target = resolve_target(args.repository, args.ref, args.server_environment) if args.command == "set-target" else None
    # mode=rw never creates an accidental empty deployment database.
    with sqlite3.connect(args.db.resolve().as_uri()+"?mode=rw", uri=True) as db:
        db.row_factory = sqlite3.Row
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='bridge_sessions'").fetchone():
            raise ValueError("Receiver has not initialized session routing")
        store = SessionStore(db, args.organization)
        if args.command != "sessions":
            db.execute("BEGIN IMMEDIATE")
            store.set_target(args.session, target)
        rows = db.execute("""SELECT session_id,thread_id,state,legacy,client_thread_id,candidate_thread_id,error,target_json
            FROM bridge_sessions WHERE organization_id=? ORDER BY created_at""", (args.organization,))
        print(json.dumps([dict(r) for r in rows], indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__}))
        raise SystemExit(1)
