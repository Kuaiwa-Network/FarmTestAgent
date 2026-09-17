import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
from farmqa_codex import CodexBridge, AppProtocolError, marker


class RolloutCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.state = root/"state.sqlite"
        (root/"sessions").mkdir()
        self.path = root/"sessions"/"rollout.jsonl"
        with closing(sqlite3.connect(self.state)) as db, db:
            db.execute("CREATE TABLE threads(id TEXT, rollout_path TEXT)")
            db.execute("INSERT INTO threads VALUES (?,?)", ("task", str(self.path)))
        self.data = {"thread": {"id": "task", "status": {"type": "idle"}},
                     "turns": [{"id": "turn", "status": "completed", "items": []}]}
        client = Mock()
        client.tool.side_effect = lambda *args, **kwargs: copy.deepcopy(self.data)
        factory = Mock()
        factory.return_value.__enter__ = Mock(return_value=client)
        factory.return_value.__exit__ = Mock(return_value=False)
        self.bridge = CodexBridge({"thread_id": "task", "state_db_path": str(self.state)}, factory)
        def event(kind, **values):
            return {"type": "event_msg", "payload": {"type": kind, "turn_id": "turn", **values}}
        self.records = [
            {"type": "session_meta", "payload": {"id": "task"}},
            event("task_started"),
            event("item_completed", thread_id="task", item={"type": "FunctionCallOutput",
                  "id": "input", "namespace": "codex_app", "name": "send_message_to_thread",
                  "output": "<codex_delegation>\n<input>"+marker("event")+"\nRemember?</input>\n</codex_delegation>"}),
            event("item_completed", thread_id="task", item={"type": "AgentMessage", "id": "final",
                  "phase": "final_answer", "content": [{"type": "Text", "text": "APPLE"}]}),
            event("task_complete", last_agent_message="APPLE")]
        self.write()

    def write(self, tail=""):
        self.path.write_text("".join(json.dumps(r)+"\n" for r in self.records)+tail, encoding="utf-8")

    def test_empty_app_turn_recovers_only_exact_event_final(self):
        self.assertEqual(self.bridge.result("event"), {"turn_id": "turn", "type": "response", "body": "APPLE"})
        self.assertIsNone(self.bridge.result("another-event"))
        with closing(sqlite3.connect(self.state)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM threads").fetchone()[0], 1)

    def test_wrong_session_or_item_thread_fails_closed(self):
        for record in (0, 2):
            with self.subTest(record=record):
                key = "id" if record == 0 else "thread_id"
                self.records[record]["payload"][key] = "wrong"
                self.write()
                with self.assertRaises(AppProtocolError):
                    self.bridge.result("event")
                self.records[record]["payload"][key] = "task"

    def test_other_turn_cannot_supply_reply(self):
        self.records[3]["payload"]["turn_id"] = "other-turn"
        self.write()
        with self.assertRaises(AppProtocolError):
            self.bridge.result("event")

    def test_incomplete_local_write_cannot_prove_completion(self):
        self.records.pop()
        self.write('{"type":"event_msg"')
        self.assertIsNone(self.bridge.result("event"))

    def test_app_running_status_still_blocks_final_delivery(self):
        self.data["turns"][0]["status"] = "inProgress"
        self.assertIsNone(self.bridge.result("event"))
        self.assertEqual(self.bridge.execution_state("event"), {"turn_id": "turn", "status": "inProgress"})

    def test_app_interruption_never_returns_normal_final(self):
        self.data["turns"][0]["status"] = "interrupted"
        self.assertEqual(self.bridge.result("event")["type"], "error")

    def test_existing_app_items_are_not_overridden(self):
        self.data["turns"][0]["items"] = [{"type": "userMessage", "content": [{"type": "text", "text": marker("event")}]},
                                              {"type": "agentMessage", "phase": "final", "text": "API reply"}]
        self.path.unlink()
        self.assertEqual(self.bridge.result("event")["body"], "API reply")

    def test_duplicate_final_fails_closed(self):
        self.records.insert(-1, copy.deepcopy(self.records[3]))
        self.write()
        with self.assertRaises(AppProtocolError):
            self.bridge.result("event")

    def test_rollout_outside_sessions_is_rejected(self):
        with closing(sqlite3.connect(self.state)) as db, db:
            db.execute("UPDATE threads SET rollout_path=?", (str(self.state.parent/"outside.jsonl"),))
        with self.assertRaises(AppProtocolError):
            self.bridge.result("event")

    @unittest.skipUnless(os.name == "nt", "Windows metadata path format")
    def test_windows_extended_path_refers_to_same_sessions_directory(self):
        with closing(sqlite3.connect(self.state)) as db, db:
            db.execute("UPDATE threads SET rollout_path=?", ("\\\\?\\"+str(self.path),))
        self.assertEqual(self.bridge.result("event")["body"], "APPLE")


if __name__ == "__main__":
    unittest.main()
