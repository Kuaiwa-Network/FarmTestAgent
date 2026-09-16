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
        self.bridge.execution_state.return_value = None
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

    def stop_event(self, **changes):
        return self.event(action="prompted", agentActivity={"id": "stop-1", "signal": "stop",
            "content": {"type": "prompt"}, **changes})

    def job(self, key=None):
        if key is None:
            return self.service.db.execute("SELECT * FROM bridge_jobs ORDER BY rowid LIMIT 1").fetchone()
        return self.service.db.execute("SELECT * FROM bridge_jobs WHERE event_key=?", (key,)).fetchone()

    def test_stop_before_dispatch_never_runs_or_returns_ordinary_reply(self):
        self.receive(self.event())
        self.assertEqual(self.receive(self.stop_event()), (200, "stop received"))
        self.step(); self.step(); self.step()
        self.assertEqual(self.status(), "cancelled")
        self.assertEqual(self.job()["stop_outcome"], "never_dispatched")
        self.assertIsNone(self.job()["input_json"])
        self.bridge.dispatch.assert_not_called()
        self.send.assert_called_once()
        self.assertIn("stopped forwarding", self.send.call_args.args[0]["content"]["body"])

    def test_stop_is_authenticated_and_bound_to_its_session(self):
        self.receive(self.event())
        bad = self.stop_event()
        self.assertEqual(self.service.receive(json.dumps(bad).encode(), "invalid")[0], 401)
        bad["organizationId"] = "wrong"
        self.assertEqual(self.receive(bad)[0], 403)
        self.assertEqual(self.receive(self.stop_event(agentSessionId="another-session"))[0], 403)
        self.assertEqual(self.job()["stop_requested"], 0)

    def test_stop_deduplicates_across_restart_and_does_not_cancel_newer_prompt(self):
        stop = self.stop_event(createdAt="2026-09-16T12:00:00Z")
        self.receive(stop); self.step(); self.restart()
        newer = self.event(action="prompted", agentActivity={"id":"new", "createdAt":"2026-09-16T12:00:01Z",
            "content":{"type":"prompt","body":"resume"}})
        self.receive(newer)
        self.assertEqual(self.receive(stop), (200, "duplicate"))
        self.step(); self.step()
        self.bridge.dispatch.assert_called_once()
        self.assertEqual(self.job()["stop_requested"], 0)

    def test_delayed_created_and_missing_time_after_stop_fail_closed(self):
        self.receive(self.stop_event(createdAt="2026-09-16T12:00:00Z")); self.step()
        self.receive(self.event(agentSession={"id":"linear-session", "createdAt":"2026-09-16T11:59:59Z"}))
        self.step()
        self.receive(self.event(action="prompted", agentActivity={"id":"unknown-time", "content":{"type":"prompt","body":"hello"}}))
        self.step()
        self.assertTrue(all(r["status"] == "cancelled" for r in self.service.results()))
        self.bridge.dispatch.assert_not_called()

    def test_queued_stop_is_scoped_to_one_linear_session(self):
        self.receive(self.event())
        self.receive(self.event(agentSession={"id":"other-session"}))
        self.receive(self.stop_event())
        for _ in range(5): self.step()
        self.bridge.dispatch.assert_called_once()
        self.assertEqual(self.bridge.dispatch.call_args.args[1]["session_id"], "other-session")

    def test_active_stop_does_not_claim_interruption_or_dispatch_another_job(self):
        self.receive(self.event()); self.step(); self.step()
        self.bridge.execution_state.return_value = {"turn_id":"running", "status":"inProgress"}
        self.receive(self.stop_event())
        self.step(); self.step()
        self.assertEqual(self.status(), "stop_pending")
        self.assertIn("not confirmed stopped", self.send.call_args.args[0]["content"]["body"])
        self.receive(self.event(agentSession={"id":"other-session"}))
        # Real scheduling keeps the stop poll in the future, allowing the queued ack.
        with self.service.db:
            self.service.db.execute("UPDATE bridge_jobs SET next_check=? WHERE stop_requested=1", (time.time()+30,))
        self.service.process_one(); self.service.process_one()
        self.bridge.dispatch.assert_called_once()
        self.bridge.execution_state.return_value = {"turn_id":"running", "status":"interrupted"}
        self.step()
        self.assertEqual(self.status(), "cancelled")
        self.assertEqual(self.job()["stop_outcome"], "interrupted")

    def test_stop_pending_survives_restart_and_only_reads_exact_turn(self):
        self.receive(self.event()); self.step(); self.step()
        self.receive(self.stop_event()); self.step(); self.step(); self.restart(); self.step()
        self.assertEqual(self.status(), "stop_pending")
        self.bridge.dispatch.assert_called_once()
        self.bridge.execution_state.assert_called_with(self.service.results()[0]["event_key"])
        self.assertEqual(self.send.call_count, 2)  # original ack and one explicit stop error

    def test_completed_after_stop_suppresses_late_final_and_records_actual_outcome(self):
        self.receive(self.event()); self.step(); self.step()
        self.receive(self.stop_event()); self.step()
        self.bridge.execution_state.return_value = {"turn_id":"turn", "status":"completed"}
        self.step(); self.step()
        self.assertEqual(self.status(), "cancelled")
        self.assertEqual(self.job()["stop_outcome"], "completed")
        self.assertIsNone(self.job()["reply_json"])
        self.bridge.result.assert_not_called()
        self.assertEqual(self.send.call_count, 2)

    def test_stop_during_idle_check_prevents_dispatch(self):
        self.receive(self.event()); self.step()
        def idle():
            self.receive(self.stop_event())
            return True
        self.bridge.is_idle.side_effect = idle
        self.step(); self.step(); self.step()
        self.bridge.dispatch.assert_not_called()
        self.assertEqual(self.status(), "cancelled")

    def test_stop_during_dispatch_preserves_hold_and_clears_private_content(self):
        self.receive(self.event()); self.step()
        self.bridge.dispatch.side_effect = lambda *_: self.receive(self.stop_event())
        self.step(); self.step(); self.step()
        self.assertEqual(self.status(), "stop_pending")
        self.assertIsNone(self.job()["input_json"])
        self.bridge.dispatch.assert_called_once()

    def test_stop_during_result_read_suppresses_ready_reply(self):
        self.receive(self.event()); self.step(); self.step()
        def result(_):
            self.receive(self.stop_event())
            return {"turn_id":"turn", "type":"response", "body":"must not send"}
        self.bridge.result.side_effect = result
        self.step()
        self.assertIsNone(self.job()["reply_json"])
        self.bridge.execution_state.return_value = {"turn_id":"turn", "status":"completed"}
        self.step(); self.step(); self.step()
        self.assertEqual(self.status(), "cancelled")
        self.assertEqual(self.send.call_count, 2)

    def test_stop_after_reply_ready_before_send_suppresses_final(self):
        self.receive(self.event()); self.step(); self.step()
        self.bridge.result.return_value = {"turn_id":"turn", "type":"response", "body":"must not send"}
        self.step(); self.receive(self.stop_event())
        self.bridge.execution_state.return_value = {"turn_id":"turn", "status":"completed"}
        self.step(); self.step(); self.step()
        self.assertEqual(self.send.call_count, 2)
        self.assertEqual(self.status(), "cancelled")

    def test_stop_cannot_recall_final_already_handed_to_linear(self):
        self.receive(self.event()); self.step(); self.step()
        self.bridge.result.return_value = {"turn_id":"turn", "type":"response", "body":"in flight"}
        self.step()
        def send(_):
            self.receive(self.stop_event())
            return {"success":True,"agentActivity":{"id":"activity"}}
        self.send.side_effect = send
        self.step()
        self.assertEqual(self.status(), "sent")
        self.assertEqual(self.service.results()[0]["error"], "StopDuringSend")
        self.assertEqual(self.job()["stop_outcome"], "reply_already_in_flight")

    def test_uncertain_dispatch_plus_stop_keeps_hold_even_if_task_is_idle(self):
        self.receive(self.event()); self.step()
        self.bridge.dispatch.side_effect = TimeoutError()
        self.step(); self.receive(self.stop_event()); self.step(); self.step()
        self.bridge.is_idle.return_value = True
        self.assertEqual(self.status(), "stop_pending")
        self.assertEqual(self.job()["stop_outcome"], "execution_not_confirmed_stopped")

    def test_stop_preserves_uncertain_final_delivery_instead_of_claiming_suppression(self):
        self.receive(self.event()); self.step(); self.step()
        self.bridge.result.return_value = {"turn_id":"turn", "type":"response", "body":"in flight"}
        self.step()
        self.send.side_effect = TimeoutError()
        self.step(); self.receive(self.stop_event()); self.step(); self.step(); self.restart(); self.step()
        self.assertEqual(self.job()["stop_outcome"], "reply_delivery_uncertain")
        self.bridge.execution_state.return_value = {"turn_id":"turn", "status":"completed"}
        self.step()
        self.assertEqual(self.job()["stop_outcome"], "completed_with_uncertain_reply_delivery")

    def test_restart_does_not_turn_ack_failure_into_possible_codex_execution(self):
        self.receive(self.event())
        self.send.side_effect = TimeoutError()
        self.step(); self.restart()
        self.assertEqual(self.job()["dispatch_started"], 0)
        self.receive(self.stop_event()); self.step(); self.step()
        self.assertEqual(self.status(), "cancelled")
        self.bridge.execution_state.assert_not_called()

    def test_stop_error_write_is_not_retried_after_timeout_or_restart(self):
        self.receive(self.event()); self.receive(self.stop_event())
        self.send.side_effect = TimeoutError()
        self.step(); self.restart(); self.step(); self.step()
        self.send.assert_called_once()
        row = self.service.db.execute("SELECT status FROM stop_requests").fetchone()
        self.assertEqual(row[0], "uncertain")
        self.assertEqual(self.status(), "cancelled")

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

    def test_execution_state_matches_exact_event_including_running_turn(self):
        self.turn["status"] = "inProgress"
        self.assertEqual(self.bridge.execution_state(self.key), {"turn_id":"turn", "status":"inProgress"})
        self.assertIsNone(self.bridge.execution_state("another-event"))


if __name__ == "__main__":
    unittest.main()
