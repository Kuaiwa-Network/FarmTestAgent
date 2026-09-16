#!/usr/bin/env python3
"""Verified Linear agent events -> fixed response or an opt-in Codex app bridge."""
import argparse
from datetime import datetime
import getpass
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import socket
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

REPLY = ("FarmQA is connected 🌱 I received your message. "
         "This is a connection test; gameplay testing is not enabled yet.")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / ".local/farmqa/config.json"
SCOPES = "read,write,app:mentionable"
MAX_BODY = 1024 * 1024


class Service:
    def __init__(self, db_path, secret, client_id, app_id, org_id, send):
        self.secret = secret.encode()
        self.identity = {"oauthClientId": client_id, "appUserId": app_id, "organizationId": org_id}
        self.send = send
        self.lock = threading.Lock()
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS events (
            event_key TEXT PRIMARY KEY, session_id TEXT NOT NULL,
            activity_id TEXT NOT NULL, status TEXT NOT NULL,
            received_at REAL NOT NULL, completed_at REAL, error TEXT)""")
        # A previous process may have sent the request without receiving its reply.
        self.db.execute("UPDATE events SET status='uncertain', error='InterruptedSend' WHERE status='sending'")
        self.db.commit()
        if str(db_path) != ":memory:":
            os.chmod(db_path, 0o600)

    def close(self):
        with self.lock:
            self.db.close()

    def receive(self, raw, signature, now_ms=None):
        expected = hmac.new(self.secret, raw, hashlib.sha256).hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
            return 401, "invalid signature"
        try:
            event = json.loads(raw)
        except (ValueError, UnicodeError):
            return 400, "invalid json"
        if not isinstance(event, dict):
            return 400, "invalid event"
        timestamp = event.get("webhookTimestamp")
        now_ms = time.time() * 1000 if now_ms is None else now_ms
        if (type(timestamp) not in (int, float) or not math.isfinite(timestamp)
                or abs(timestamp - now_ms) > 60_000):
            return 401, "invalid timestamp"
        if event.get("type") != "AgentSessionEvent":
            return 200, "ignored"
        if any(event.get(k) != v for k, v in self.identity.items()):
            return 403, "identity mismatch"
        action = event.get("action")
        if action not in ("created", "prompted"):
            return 200, "ignored"
        session = event.get("agentSession")
        session_id = session.get("id") if isinstance(session, dict) else None
        if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
            return 400, "missing session"
        event_id = session_id
        if action == "prompted":
            activity = event.get("agentActivity")
            if not isinstance(activity, dict) or not activity.get("id"):
                return 400, "missing prompt"
            content = activity.get("content")
            if not isinstance(content, dict) or content.get("type") != "prompt":
                return 200, "ignored"
            event_id = activity["id"]
            if not isinstance(event_id, str) or len(event_id) > 128:
                return 400, "invalid prompt id"
            if activity.get("agentSessionId", session_id) != session_id:
                return 403, "activity session mismatch"
            if activity.get("signal") == "stop":
                return self.receive_stop(event)
        key = f"{self.identity['organizationId']}:{action}:{event_id}"
        try:
            prepared = self.prepare_event(event)
        except ValueError:
            return 400, "invalid prompt"
        with self.lock, self.db:
            cursor = self.db.execute("INSERT OR IGNORE INTO events VALUES (?, ?, ?, 'pending', ?, NULL, NULL)",
                                     (key, session_id, str(uuid.uuid4()), time.time()))
            inserted = cursor.rowcount > 0
            if inserted:
                self.enqueue(key, prepared)
        return 200, "accepted" if inserted else "duplicate"

    def prepare_event(self, event):
        return None

    def receive_stop(self, event):
        # Never interpret a control signal as an ordinary fixed-reply prompt.
        with self.lock, self.db:
            key = f"{self.identity['organizationId']}:stop:{event['agentActivity']['id']}"
            inserted = self.db.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,'cancelled',?,?,NULL)",
                (key, event["agentSession"]["id"], str(uuid.uuid4()), time.time(), time.time())).rowcount
            if inserted:
                self.db.execute("""UPDATE events SET status='cancelled',completed_at=?
                    WHERE session_id=? AND status='pending'""",
                    (time.time(), event["agentSession"]["id"]))
        return 200, "stop received" if inserted else "duplicate"

    def enqueue(self, key, prepared):
        pass

    def process_one(self):
        with self.lock, self.db:
            row = self.db.execute("SELECT * FROM events WHERE status='pending' ORDER BY received_at LIMIT 1").fetchone()
            if row is None:
                return False
            self.db.execute("UPDATE events SET status='sending' WHERE event_key=?", (row["event_key"],))
        status, error = "sent", None
        try:
            result = self.send({"id": row["activity_id"], "agentSessionId": row["session_id"],
                                "content": {"type": "response", "body": REPLY}})
            if not isinstance(result, dict) or result.get("success") is not True or not result.get("agentActivity", {}).get("id"):
                raise RuntimeError("Linear did not confirm activity creation")
        except Exception as exc:
            status, error = "uncertain", type(exc).__name__
        with self.lock, self.db:
            self.db.execute("UPDATE events SET status=?, completed_at=?, error=? WHERE event_key=?",
                            (status, time.time(), error, row["event_key"]))
        print(json.dumps({"event": "reply", "session_id": row["session_id"],
                          "activity_id": row["activity_id"], "status": status, "error": error}), flush=True)
        return True

    def results(self):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM events ORDER BY received_at")]


class BridgeService(Service):
    """One desktop task, serialized prompts, durable stages, no ambiguous resends."""
    def __init__(self, *args, bridge, **kwargs):
        super().__init__(*args, **kwargs)
        self.bridge = bridge
        self.db.execute("""CREATE TABLE IF NOT EXISTS bridge_jobs (
            event_key TEXT PRIMARY KEY, input_json TEXT, ack_id TEXT NOT NULL,
            thread_id TEXT NOT NULL, turn_id TEXT, reply_json TEXT,
            next_check REAL NOT NULL DEFAULT 0, deadline REAL NOT NULL)""")
        columns = {r[1] for r in self.db.execute("PRAGMA table_info(bridge_jobs)")}
        for name, definition in (("source_ms", "REAL"), ("stop_requested", "INTEGER NOT NULL DEFAULT 0"),
                                 ("dispatch_started", "INTEGER NOT NULL DEFAULT 0"), ("stop_outcome", "TEXT")):
            if name not in columns:
                self.db.execute(f"ALTER TABLE bridge_jobs ADD COLUMN {name} {definition}")
        # Migration preserves possible execution even if an old dispatch was ambiguous.
        if "dispatch_started" not in columns:
            self.db.execute("""UPDATE bridge_jobs SET dispatch_started=1 WHERE event_key IN
                (SELECT event_key FROM events WHERE status IN
                 ('dispatching','waiting','reply_ready','sending','sent','uncertain','stop_pending'))""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS stop_requests (
            stop_key TEXT PRIMARY KEY, session_id TEXT NOT NULL, cutoff_ms REAL NOT NULL,
            activity_id TEXT NOT NULL, status TEXT NOT NULL, received_at REAL NOT NULL,
            completed_at REAL, error TEXT)""")
        self.db.execute("""UPDATE stop_requests SET status='uncertain',error='InterruptedStopReply'
            WHERE status='sending'""")
        self.db.execute("""UPDATE events SET status='uncertain', error='InterruptedBridgeSend'
                           WHERE status IN ('acknowledging', 'dispatching')""")
        self.db.commit()

    @staticmethod
    def source_time(event):
        source = event.get("agentActivity") if event["action"] == "prompted" else event["agentSession"]
        value = source.get("createdAt") if isinstance(source, dict) else None
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.timestamp() * 1000 if parsed.tzinfo else None
        except ValueError:
            return None

    def receive_stop(self, event):
        session_id = event["agentSession"]["id"]
        stop_key = f"{self.identity['organizationId']}:stop:{event['agentActivity']['id']}"
        cutoff = self.source_time(event)
        cutoff = event["webhookTimestamp"] if cutoff is None else cutoff
        with self.lock, self.db:
            inserted = self.db.execute("INSERT OR IGNORE INTO stop_requests VALUES (?,?,?,?, 'pending',?,NULL,NULL)",
                (stop_key, session_id, cutoff, str(uuid.uuid4()), time.time())).rowcount
            if inserted:
                self.db.execute("""UPDATE bridge_jobs SET stop_outcome='reply_delivery_uncertain'
                    WHERE reply_json IS NOT NULL AND event_key IN
                    (SELECT event_key FROM events WHERE session_id=? AND status IN ('sending','uncertain'))
                    AND (source_ms IS NULL OR source_ms<=?)""", (session_id, cutoff))
                self.db.execute("""UPDATE bridge_jobs SET stop_requested=1,next_check=0,
                    input_json=NULL,reply_json=NULL WHERE event_key IN
                    (SELECT event_key FROM events WHERE session_id=? AND status NOT IN ('sent','cancelled'))
                    AND (source_ms IS NULL OR source_ms<=?)""", (session_id, cutoff))
        return 200, "stop received" if inserted else "duplicate"

    def prepare_event(self, event):
        session = event["agentSession"]
        issue = session.get("issue") or {}
        if not isinstance(issue, dict):
            raise ValueError("Invalid issue")
        if event["action"] == "prompted":
            prompt = event["agentActivity"]["content"].get("body")
        else:
            prompt = event.get("promptContext") or (session.get("comment") or {}).get("body")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 32000:
            raise ValueError("Missing or oversized prompt")
        url = issue.get("url", "")
        if not isinstance(url, str) or len(url) > 2000:
            raise ValueError("Invalid issue URL")
        return {"session_id": session["id"], "issue_url": url, "prompt": prompt,
                "source_ms": self.source_time(event)}

    def enqueue(self, key, prepared):
        source_ms = prepared.pop("source_ms")
        cutoff = self.db.execute("SELECT max(cutoff_ms) FROM stop_requests WHERE session_id=?",
                                 (prepared["session_id"],)).fetchone()[0]
        stopped = cutoff is not None and (source_ms is None or source_ms <= cutoff)
        self.db.execute("""INSERT INTO bridge_jobs
            (event_key,input_json,ack_id,thread_id,deadline,source_ms,stop_requested) VALUES (?,?,?,?,?,?,?)""",
            (key, None if stopped else json.dumps(prepared), str(uuid.uuid4()), self.bridge.thread_id,
             time.time() + 900, source_ms, int(stopped)))

    def _update(self, row, status, error=None, claim=False, **fields):
        with self.lock, self.db:
            stopped = self.db.execute("SELECT stop_requested FROM bridge_jobs WHERE event_key=?",
                                      (row["event_key"],)).fetchone()[0]
            if claim and stopped:
                return False
            if stopped:
                fields.update(input_json=None, reply_json=None)
                if status == "sent":
                    # A request already handed to Linear cannot be recalled.
                    error = "StopDuringSend"
                    fields["stop_outcome"] = "reply_already_in_flight"
                elif status == "uncertain" and row["status"] == "reply_ready":
                    fields["stop_outcome"] = "reply_delivery_uncertain"
            self.db.execute("UPDATE events SET status=?,error=?,completed_at=? WHERE event_key=?",
                            (status, error, time.time() if status in ("sent", "uncertain", "cancelled") else None,
                             row["event_key"]))
            for name, value in fields.items():
                if name not in ("turn_id", "reply_json", "next_check", "input_json", "dispatch_started", "stop_outcome"):
                    raise ValueError("Invalid ledger field")
                self.db.execute(f"UPDATE bridge_jobs SET {name}=? WHERE event_key=?", (value, row["event_key"]))
        if status in ("sent", "uncertain", "cancelled"):
            print(json.dumps({"event": "bridge", "session_id": row["session_id"],
                              "thread_id": row["thread_id"], "status": status, "error": error}), flush=True)
        return True

    def _process_stop_reply(self):
        with self.lock, self.db:
            row = self.db.execute("SELECT * FROM stop_requests WHERE status='pending' ORDER BY received_at LIMIT 1").fetchone()
            if row is None:
                return False
            active = self.db.execute("""SELECT 1 FROM events e JOIN bridge_jobs b USING(event_key)
                WHERE e.session_id=? AND b.stop_requested=1 AND b.dispatch_started=1
                AND e.status NOT IN ('sent','cancelled') LIMIT 1""", (row["session_id"],)).fetchone()
            self.db.execute("UPDATE stop_requests SET status='sending' WHERE stop_key=?", (row["stop_key"],))
        if active:
            content = {"type": "error", "body": "Stop received. Pending replies are suppressed. "
                "Active Codex work is not confirmed stopped: this desktop connector cannot interrupt it. "
                "Click Stop in FarmQA Linear inbox in Codex. No new work will be dispatched until the matching turn ends."}
        else:
            content = {"type": "response", "body": "FarmQA stopped forwarding pending work for this session. "
                "No pending Codex execution remains for the stopped requests."}
        status, error = "sent", None
        try:
            self._send(row, row["activity_id"], content)
        except Exception as exc:
            status, error = "uncertain", type(exc).__name__
        with self.lock, self.db:
            self.db.execute("UPDATE stop_requests SET status=?,completed_at=?,error=? WHERE stop_key=?",
                            (status, time.time(), error, row["stop_key"]))
        return True

    def _process_stopped(self, row):
        if not row["dispatch_started"]:
            self._update(row, "cancelled", stop_outcome="never_dispatched", input_json=None, reply_json=None)
            return
        try:
            state = self.bridge.execution_state(row["event_key"])
            if state and state["status"] in ("completed", "interrupted", "failed"):
                outcome = state["status"]
                if row["stop_outcome"] == "reply_delivery_uncertain":
                    outcome += "_with_uncertain_reply_delivery"
                self._update(row, "cancelled", turn_id=state["turn_id"],
                             stop_outcome=outcome, input_json=None, reply_json=None)
            else:
                self._update(row, "stop_pending", "DesktopInterruptUnavailable", next_check=time.time()+3,
                             stop_outcome=row["stop_outcome"] or "execution_not_confirmed_stopped")
        except Exception as exc:
            self._update(row, "stop_pending", type(exc).__name__, next_check=time.time()+10)

    def _send(self, row, activity_id, content):
        result = self.send({"id": activity_id, "agentSessionId": row["session_id"], "content": content})
        if not isinstance(result, dict) or result.get("success") is not True or not result.get("agentActivity", {}).get("id"):
            raise RuntimeError("Linear did not confirm activity creation")

    def process_one(self):
        now = time.time()
        with self.lock:
            row = self.db.execute("""SELECT e.*,b.* FROM events e JOIN bridge_jobs b USING(event_key)
                WHERE (e.status IN ('pending','queued','waiting','reply_ready') OR
                    (b.stop_requested=1 AND e.status IN ('stop_pending','uncertain'))) AND b.next_check<=?
                ORDER BY b.stop_requested DESC, CASE e.status WHEN 'pending' THEN 0 WHEN 'reply_ready' THEN 1
                    WHEN 'waiting' THEN 2 ELSE 3 END, e.received_at LIMIT 1""", (now,)).fetchone()
            busy = self.db.execute("""SELECT 1 FROM events e JOIN bridge_jobs b USING(event_key)
                WHERE b.dispatch_started=1 AND e.status NOT IN ('sent','cancelled') LIMIT 1""").fetchone()
        if self._process_stop_reply():
            return True
        if row is None:
            return False
        if row["thread_id"] != self.bridge.thread_id:
            self._update(row, "uncertain", "DestinationChanged", next_check=now+10)
            return True
        if row["stop_requested"]:
            self._process_stopped(row)
            return True
        status = row["status"]
        if status == "pending":
            if not self._update(row, "acknowledging", claim=True):
                return True
            try:
                self._send(row, row["ack_id"], {"type": "thought",
                    "body": "FarmQA received your message. It is queued for the Codex app task."})
                self._update(row, "queued")
            except Exception as exc:
                self._update(row, "uncertain", type(exc).__name__)
        elif status in ("queued", "waiting"):
            if now > row["deadline"]:
                self._update(row, "reply_ready", "CodexTimeout", reply_json=json.dumps({"type": "error",
                    "body": "A Codex result was not confirmed in time. Inspect FarmQA Linear inbox in Codex before retrying."}))
                return True
            if status == "queued":
                try:
                    if busy or not self.bridge.is_idle():
                        self._update(row, "queued", next_check=now + 5)
                        return False
                except Exception as exc:
                    self._update(row, "queued", type(exc).__name__, next_check=now + 10)
                    return False  # Read-only availability checks may be retried.
                if not self._update(row, "dispatching", claim=True, dispatch_started=1):
                    return True
                try:
                    self.bridge.dispatch(row["event_key"], json.loads(row["input_json"]))
                    self._update(row, "waiting", next_check=now + 3)
                except Exception as exc:
                    self._update(row, "uncertain", type(exc).__name__)
            else:
                try:
                    result = self.bridge.result(row["event_key"])
                    if result is None:
                        self._update(row, "waiting", next_check=now + 3)
                    else:
                        self._update(row, "reply_ready", turn_id=result["turn_id"],
                                     reply_json=json.dumps({"type": result["type"], "body": result["body"]}))
                except Exception as exc:
                    self._update(row, "waiting", type(exc).__name__, next_check=now + 10)
        else:
            if not self._update(row, "sending", claim=True):
                return True
            try:
                self._send(row, row["activity_id"], json.loads(row["reply_json"]))
                self._update(row, "sent", row["error"], input_json=None, reply_json=None)
            except Exception as exc:
                self._update(row, "uncertain", type(exc).__name__)
        return True


class LinearAPI:
    def __init__(self, client_id, client_secret, request=None):
        self.client_id, self.client_secret = client_id, client_secret
        self.request = request or urllib.request.urlopen
        self.token, self.expires = None, 0

    def _request(self, url, data, headers):
        req = urllib.request.Request(url, data=data, headers=headers)
        with self.request(req, timeout=8) as response:
            return json.load(response)

    def authenticate(self):
        result = self._request("https://api.linear.app/oauth/token", urllib.parse.urlencode({
            "grant_type": "client_credentials", "client_id": self.client_id,
            "client_secret": self.client_secret, "scope": SCOPES}).encode(),
            {"Content-Type": "application/x-www-form-urlencoded"})
        self.token = result["access_token"]
        self.expires = time.time() + float(result["expires_in"]) - 60

    def graphql(self, query, variables=None):
        if not self.token or time.time() >= self.expires:
            self.authenticate()
        for attempt in range(2):
            try:
                result = self._request("https://api.linear.app/graphql",
                    json.dumps({"query": query, "variables": variables or {}}).encode(),
                    {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"})
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 401 or attempt:
                    raise
                self.authenticate()  # 401 means the mutation was not authorized.
        if result.get("errors") or not isinstance(result.get("data"), dict):
            raise RuntimeError("Linear GraphQL rejected the request")
        return result["data"]

    def identity(self):
        data = self.graphql("query FarmQAIdentity { viewer { id name } organization { id name } }")
        if data["viewer"]["name"] != "FarmQA":
            raise RuntimeError("Expected FarmQA app identity")
        return data

    def send(self, activity):
        return self.graphql("""mutation FarmQAReply($input: AgentActivityCreateInput!) {
            agentActivityCreate(input: $input) { success agentActivity { id } }
        }""", {"input": activity})["agentActivityCreate"]


def make_server(service, port=8765):
    class ExclusiveServer(ThreadingHTTPServer):
        # Windows SO_REUSEADDR permits two live listeners on the same port.
        allow_reuse_address = os.name != "nt"

        def server_bind(self):
            if os.name == "nt":
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Never log URLs, headers, prompts or credentials.

        def respond(self, status, message):
            data = json.dumps({"status": message}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.respond(200, "FarmQA ready") if self.path == "/health" else self.respond(404, "not found")

        def do_POST(self):
            if self.path != "/webhook":
                return self.respond(404, "not found")
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self.respond(400, "invalid length")
            if length <= 0 or length > MAX_BODY:
                return self.respond(413, "invalid body size")
            self.connection.settimeout(3)
            try:
                raw = self.rfile.read(length)
                if len(raw) != length:
                    return self.respond(400, "incomplete body")
                status, message = self.server.service.receive(raw, self.headers.get("Linear-Signature"))
            except TimeoutError:
                return self.respond(408, "body timeout")
            except Exception:
                return self.respond(500, "receiver error")
            self.respond(status, message)
    server = ExclusiveServer(("127.0.0.1", port), Handler)
    server.service = service
    server.daemon_threads = True
    return server


def configure(path):
    if path.exists():
        raise RuntimeError("Config already exists; edit it locally to avoid replacing credentials")
    config = {"client_id": input("Linear FarmQA client ID: ").strip(),
              "client_secret": getpass.getpass("Linear client secret (hidden): ").strip(),
              "webhook_secret": getpass.getpass("Linear webhook signing secret (hidden): ").strip()}
    if not all(config.values()):
        raise ValueError("All three fields are required")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as file:
        json.dump(config, file, indent=2)
    print(f"Saved private configuration to {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["configure", "serve", "status"])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.command == "configure":
        return configure(args.config)
    db_path = args.config.parent / "events.sqlite3"
    if args.command == "status":
        if not db_path.exists():
            print("No event database yet.")
            return
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            print(json.dumps([dict(row) for row in db.execute("SELECT * FROM events ORDER BY received_at")], indent=2))
        return
    config = json.loads(args.config.read_text())
    if any(not isinstance(config.get(k), str) or not config[k].strip()
           for k in ("client_id", "client_secret", "webhook_secret")):
        raise ValueError("Configuration is incomplete")
    os.chmod(args.config, 0o600)
    api = LinearAPI(config["client_id"], config["client_secret"])
    identity = api.identity()
    # Reserve the listening port before opening/recovering the delivery ledger.
    # A second receiver must not mark an active send from the first uncertain.
    server = make_server(None, args.port)
    try:
        service_args = (db_path, config["webhook_secret"], config["client_id"],
                        identity["viewer"]["id"], identity["organization"]["id"], api.send)
        if config.get("mode", "fixed") == "codex":
            from farmqa_codex import CodexBridge
            bridge = CodexBridge(json.loads((args.config.parent / "codex.json").read_text()))
            service = BridgeService(*service_args, bridge=bridge)
        elif config.get("mode", "fixed") == "fixed":
            service = Service(*service_args)
        else:
            raise ValueError("Unknown FarmQA mode")
    except Exception:
        server.server_close()
        raise
    server.service = service
    stop = threading.Event()
    def work():
        while not stop.is_set():
            if not service.process_one():
                stop.wait(0.1)
    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    print(json.dumps({"event": "ready", "app": identity["viewer"], "workspace": identity["organization"],
                      "listen": f"http://127.0.0.1:{args.port}", "mode": config.get("mode", "fixed")}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        stop.set()
        worker.join(timeout=20)
        if not worker.is_alive():
            service.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Remote responses and configuration must not leak through tracebacks.
        print(f"FarmQA stopped: {type(error).__name__}. Check local configuration and Linear app settings.", flush=True)
        raise SystemExit(1)
