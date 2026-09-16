import hashlib
import hmac
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from linear_farmqa import BridgeService
from farmqa_codex import CodexBridge, AppProtocolError, marker


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "events.sqlite3"
        self.bridge = Mock(thread_id="desktop-task")
        self.bridge.is_idle.return_value = True
        self.bridge.result.return_value = None
        self.send = Mock(return_value={"success": True, "agentActivity": {"id": "activity"}})
        self.service = self.open_service()

    def open_service(self):
        service = BridgeService(self.db, "secret", "client", "app", "org", self.send, bridge=self.bridge)
        self.addCleanup(service.close)
        return service

    def event(self, **changes):
        event = {"type": "AgentSessionEvent", "action": "created", "webhookTimestamp": int(time.time()*1000),
                 "oauthClientId": "client", "appUserId": "app", "organizationId": "org",
                 "agentSession": {"id": "linear-session", "issue": {"url": "https://linear.app/w/issue/FARM-1"}},
                 "promptContext": "Hello from Linear"}
        event.update(changes)
        return event

    def receive(self, event):
        raw = json.dumps(event).encode()
        return self.service.receive(raw, hmac.new(b"secret", raw, hashlib.sha256).hexdigest())

    def step(self):
        with self.service.db:
            self.service.db.execute("UPDATE bridge_jobs SET next_check=0")
        return self.service.process_one()

    def status(self):
        return self.service.results()[0]["status"]

    def restart(self):
        # Remove the old cleanup before closing this connection exactly once.
        old = self.service
        self._cleanups = [c for c in self._cleanups if c[0] != old.close]
        old.close()
        self.service = self.open_service()

    def test_signed_message_roundtrip_duplicates_and_private_content_cleanup(self):
        event = self.event()
        self.assertEqual(self.receive(event), (200, "accepted"))
        self.assertEqual(self.receive(event), (200, "duplicate"))
        self.step()  # acknowledge
        self.assertEqual(self.send.call_args.args[0]["content"]["type"], "thought")
        self.step()  # dispatch
        self.assertEqual(self.status(), "waiting")
        key = self.service.results()[0]["event_key"]
        self.bridge.dispatch.assert_called_once()
        self.assertEqual(self.bridge.dispatch.call_args.args[1]["prompt"], "Hello from Linear")
        self.bridge.result.return_value = {"turn_id": "turn-1", "type": "response", "body": "Actual Codex reply"}
        self.step()
        self.step()
        self.assertEqual(self.status(), "sent")
        self.assertEqual(self.send.call_args.args[0]["content"]["body"], "Actual Codex reply")
        self.assertNotIn("prompt", self.service.results()[0])
        row = self.service.db.execute("SELECT * FROM bridge_jobs WHERE event_key=?", (key,)).fetchone()
        self.assertIsNone(row["input_json"])
        self.assertIsNone(row["reply_json"])
        self.assertEqual(row["turn_id"], "turn-1")

    def test_followup_uses_same_task_and_nested_prompt_body(self):
        event = self.event(action="prompted", agentActivity={"id": "followup", "content": {"type": "prompt", "body": "again"}})
        self.receive(event)
        self.step(); self.step()
        self.assertEqual(self.bridge.dispatch.call_args.args[1]["prompt"], "again")
        self.assertEqual(self.service.db.execute("SELECT thread_id FROM bridge_jobs").fetchone()[0], "desktop-task")

    def test_no_execution_for_unsigned_or_wrong_identity_events(self):
        self.assertEqual(self.service.receive(json.dumps(self.event()).encode(), "bad")[0], 401)
        self.assertEqual(self.receive(self.event(organizationId="other"))[0], 403)
        self.assertFalse(self.step())
        self.bridge.dispatch.assert_not_called()

    def test_missing_prompt_rejected_without_ledger_entry(self):
        self.assertEqual(self.receive(self.event(promptContext=None))[0], 400)
        self.assertEqual(self.service.results(), [])

    def test_unavailable_app_only_retries_read_checks(self):
        self.receive(self.event()); self.step()
        self.bridge.is_idle.side_effect = TimeoutError()
        self.step(); self.step()
        self.assertEqual(self.status(), "queued")
        self.bridge.dispatch.assert_not_called()

    def test_ambiguous_dispatch_is_never_retried(self):
        self.receive(self.event()); self.step()
        self.bridge.dispatch.side_effect = TimeoutError()
        self.step(); self.restart(); self.step()
        self.assertEqual(self.status(), "uncertain")
        self.bridge.dispatch.assert_called_once()

    def test_restart_waiting_only_reads_existing_result(self):
        self.receive(self.event()); self.step(); self.step()
        self.restart(); self.step()
        self.assertEqual(self.status(), "waiting")
        self.bridge.dispatch.assert_called_once()

    def test_restart_during_dispatch_fails_closed(self):
        self.receive(self.event())
        with self.service.db:
            self.service.db.execute("UPDATE events SET status='dispatching'")
        self.restart(); self.step()
        self.assertEqual(self.status(), "uncertain")
        self.bridge.dispatch.assert_not_called()

    def test_second_message_waits_for_first_but_is_acknowledged(self):
        self.receive(self.event()); self.step(); self.step()
        self.receive(self.event(action="prompted", agentActivity={"id":"second", "content":{"type":"prompt","body":"second"}}))
        self.step(); self.step(); self.step()
        self.assertEqual(self.send.call_count, 2)
        self.bridge.dispatch.assert_called_once()

    def test_final_send_timeout_is_not_retried_after_restart(self):
        self.receive(self.event()); self.step(); self.step()
        self.bridge.result.return_value = {"turn_id":"turn", "type":"response", "body":"reply"}
        self.step()
        self.send.side_effect = TimeoutError()
        self.step(); self.restart(); self.step()
        self.assertEqual(self.status(), "uncertain")
        self.assertEqual(self.send.call_count, 2)


class ResultCorrelationTests(unittest.TestCase):
    def setUp(self):
        self.bridge = CodexBridge({"thread_id":"task"})
        self.key = "org:prompted:123"
        self.turn = {"id":"turn", "status":"completed", "items":[
            {"type":"userMessage", "content":[{"type":"text", "text":marker(self.key)+"\nhello"}]},
            {"type":"agentMessage", "phase":"commentary", "text":"working"},
            {"type":"agentMessage", "phase":"final_answer", "text":"real reply"}]}
        self.bridge.read = Mock(return_value={"turns":[self.turn]})

    def test_only_matching_event_final_is_returned(self):
        self.assertEqual(self.bridge.result(self.key)["body"], "real reply")
        self.assertIsNone(self.bridge.result("different"))

    def test_in_progress_text_is_not_a_completed_result(self):
        self.turn["status"] = "inProgress"
        self.assertIsNone(self.bridge.result(self.key))

    def test_desktop_delegation_output_is_correlated(self):
        self.turn["items"][0] = {"type":"functionCallOutput", "namespace":"codex_app",
                                 "name":"send_message_to_thread", "output":{"text":marker(self.key)}}
        self.assertEqual(self.bridge.result(self.key)["turn_id"], "turn")
        self.turn["items"][0]["name"] = "unrelated_tool"
        self.assertIsNone(self.bridge.result(self.key))

    def test_completed_without_final_does_not_report_success(self):
        self.turn["items"].pop()
        with self.assertRaises(AppProtocolError):
            self.bridge.result(self.key)


if __name__ == "__main__":
    unittest.main()
