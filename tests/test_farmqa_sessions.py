import json
from contextlib import closing
import os
import sqlite3
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from farmqa_codex import AppProtocolError, CodexBridge, binding_marker, configure
from farmqa_state import resolve_target
import test_farmqa_codex as helpers


class SessionRoutingTests(unittest.TestCase):
    open_service = helpers.BridgeTests.open_service
    event = helpers.BridgeTests.event
    receive = helpers.BridgeTests.receive
    restart = helpers.BridgeTests.restart
    job = helpers.BridgeTests.job

    def stop_event(self, **changes):
        session = changes.pop("agentSession", {"id":"a"})
        event = helpers.BridgeTests.stop_event(self, **changes)
        event["agentSession"] = session
        return event

    def setUp(self):
        helpers.BridgeTests.setUp(self)
        self.bridge.session_routing = True
        self.bridge.session_target.return_value = {"type": "project"}
        self.bridge.find_session.return_value = None
        self.bridge.session_initialized.return_value = True
        self.tasks = {}
        def create(*_):
            task_id = "task-" + str(len(self.tasks)+1)
            self.task(task_id)
            return {"thread_id": task_id}
        self.bridge.create_session.side_effect = create
        self.bridge.for_thread.side_effect = self.task

    def task(self, task_id):
        if task_id not in self.tasks:
            task = Mock(thread_id=task_id)
            task.is_idle.return_value = True
            task.result.return_value = None
            task.execution_state.return_value = None
            self.tasks[task_id] = task
        return self.tasks[task_id]

    def step(self, count=1):
        for _ in range(count):
            with self.service.db:
                self.service.db.execute("UPDATE bridge_jobs SET next_check=0")
                self.service.db.execute("UPDATE bridge_sessions SET next_check=0")
            self.service.process_one()

    def add(self, session_id, activity=None):
        changes = {"agentSession": {"id": session_id,
            "issue": {"url": "https://linear.app/w/issue/FARM-1"}}}
        if activity:
            changes.update(action="prompted", agentActivity={"id": activity,
                "content": {"type": "prompt", "body": activity}})
        self.receive(self.event(**changes))

    def test_distinct_sessions_on_same_issue_dispatch_and_reply_independently(self):
        self.add("a"); self.step(3)
        self.add("b")
        # Leave A's poll in the future, as the normal scheduler does.
        self.service.process_one(); self.service.process_one(); self.service.process_one()
        self.assertEqual(set(self.tasks), {"task-1", "task-2"})
        for task in self.tasks.values():
            task.dispatch.assert_called_once()
        self.assertEqual(self.task("task-1").dispatch.call_args.args[1]["session_id"], "a")
        self.assertEqual(self.task("task-2").dispatch.call_args.args[1]["session_id"], "b")
        for session_id, task_id in (("a", "task-1"), ("b", "task-2")):
            self.task(task_id).result.return_value = {"turn_id": "turn-"+session_id,
                "type": "response", "body": "reply-"+session_id}
        self.step(4)
        replies = [call.args[0] for call in self.send.call_args_list if call.args[0]["content"]["type"] == "response"]
        self.assertEqual({r["agentSessionId"]: r["content"]["body"] for r in replies},
                         {"a": "reply-a", "b": "reply-b"})

    def test_followup_keeps_mapping_after_restart_and_waits_for_first(self):
        self.add("a"); self.step(3)
        self.add("a", "second"); self.restart()
        self.service.process_one(); self.service.process_one()
        self.task("task-1").dispatch.assert_called_once()
        self.task("task-1").result.return_value = {"turn_id":"first", "type":"response", "body":"done"}
        self.step(2)
        self.task("task-1").result.return_value = None
        self.step()
        self.assertEqual(self.task("task-1").dispatch.call_count, 2)
        self.bridge.create_session.assert_called_once()

    def test_delayed_earlier_job_cannot_be_overtaken(self):
        self.add("a"); self.step()  # First is queued, not dispatched.
        self.add("a", "second"); self.service.process_one()
        with self.service.db:
            self.service.db.execute("UPDATE bridge_jobs SET next_check=? WHERE event_key='org:created:a'",
                                    (time.time()+60,))
        self.assertFalse(self.service.process_one())
        self.bridge.create_session.assert_not_called()

    def test_pending_client_id_is_never_used_as_task_id(self):
        self.bridge.create_session.side_effect = None
        self.bridge.create_session.return_value = {"client_thread_id":"pending-client"}
        self.add("a"); self.step(2); self.restart(); self.step()
        self.bridge.create_session.assert_called_once()
        self.assertEqual(self.job()["thread_id"], "")
        self.bridge.for_thread.assert_not_called()
        self.bridge.find_session.return_value = "actual-task"
        self.step(2)
        self.task("actual-task").dispatch.assert_called_once()
        self.assertEqual(self.job()["thread_id"], "actual-task")

    def test_ready_task_id_waits_for_bootstrap_completion_before_dispatch(self):
        self.bridge.session_initialized.return_value = False
        self.add("a"); self.step(2); self.restart(); self.step()
        self.assertEqual(self.job()["thread_id"], "")
        self.task("task-1").dispatch.assert_not_called()
        self.bridge.session_initialized.return_value = True
        self.step(2)
        self.task("task-1").dispatch.assert_called_once()
        self.bridge.create_session.assert_called_once()

    def test_ambiguous_task_creation_recovers_by_read_without_creating_again(self):
        self.bridge.create_session.side_effect = TimeoutError()
        self.add("a"); self.step(2); self.restart(); self.step()
        self.assertEqual(self.service.sessions.get("a")["state"], "uncertain")
        token = self.service.sessions.get("a")["binding_token"]
        self.bridge.find_session.assert_called_with(token)
        self.bridge.find_session.return_value = "recovered-task"
        self.step(2)
        self.bridge.create_session.assert_called_once()
        self.task("recovered-task").dispatch.assert_called_once()

    def test_restart_during_creation_never_repeats_mutation(self):
        self.add("a"); self.step()
        with self.service.db:
            self.service.db.execute("UPDATE bridge_sessions SET state='creating'")
        self.restart(); self.step()
        self.bridge.create_session.assert_not_called()
        self.bridge.find_session.assert_called_once()

    def test_stop_before_creation_and_during_discovery_prevents_creation(self):
        self.add("a"); self.step()
        def discover():
            self.receive(self.stop_event(agentSession={"id":"a"}))
            return {"type":"project"}
        self.bridge.session_target.side_effect = discover
        self.step(3)
        self.bridge.create_session.assert_not_called()
        self.assertEqual(self.job()["stop_outcome"], "never_dispatched")

    def test_stop_during_bootstrap_prevents_user_message_dispatch(self):
        def create(*_):
            self.receive(self.stop_event(agentSession={"id":"a"}))
            return {"thread_id":"bootstrap-only"}
        self.bridge.create_session.side_effect = create
        self.add("a"); self.step(5)
        self.assertEqual(self.job()["stop_outcome"], "never_dispatched")
        self.bridge.for_thread.assert_not_called()

    def test_stop_of_active_session_does_not_hold_another_task(self):
        self.add("a"); self.step(3)
        self.receive(self.stop_event(agentSession={"id":"a"})); self.step(2)
        self.add("b")
        self.service.process_one(); self.service.process_one(); self.service.process_one()
        self.task("task-2").dispatch.assert_called_once()
        self.assertEqual(self.job()["stop_outcome"], "execution_not_confirmed_stopped")
        stop_reply = self.send.call_args_list[1].args[0]["content"]["body"]
        self.assertIn("task-1", stop_reply)
        self.assertNotIn("task-2", stop_reply)

    def test_migration_keeps_existing_sessions_in_legacy_inbox(self):
        self.bridge.session_routing = False
        self.add("a"); self.step(2)
        with self.service.db:
            self.service.db.execute("DROP TABLE bridge_sessions")
        self.bridge.session_routing = True
        self.restart()
        self.assertEqual(self.service.sessions.get("a")["thread_id"], "desktop-task")
        self.assertEqual(self.service.sessions.get("a")["legacy"], 1)
        self.bridge.dispatch.assert_called_once()
        self.bridge.create_session.assert_not_called()

    def test_task_cannot_be_bound_to_two_sessions(self):
        self.add("a"); self.step(3)
        self.bridge.create_session.side_effect = None
        self.bridge.create_session.return_value = {"thread_id":"task-1"}
        self.add("b"); self.service.process_one(); self.service.process_one()
        self.assertIsNone(self.service.sessions.get("b")["thread_id"])
        self.task("task-1").dispatch.assert_called_once()

    def test_each_queued_request_keeps_target_snapshot(self):
        self.add("a")
        old_target = {"commit_sha":"a"*40, "requested_ref":"refs/heads/qa"}
        new_target = {"commit_sha":"b"*40, "requested_ref":"refs/heads/qa"}
        with self.service.db:
            self.service.sessions.set_target("a", old_target)
        self.add("a", "pinned-old")
        with self.service.db:
            self.service.sessions.set_target("a", new_target)
        self.add("a", "pinned-new"); self.restart()
        self.assertIsNone(self.job("org:created:a")["target_json"])
        self.assertEqual(json.loads(self.job("org:prompted:pinned-old")["target_json"]), old_target)
        payload = json.loads(self.job("org:prompted:pinned-new")["input_json"])
        self.assertEqual(payload["target"], new_target)


class TargetResolutionTests(unittest.TestCase):
    def test_branch_moves_do_not_change_existing_snapshot_or_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.run(["git", "-C", directory, *args], check=True,
                    capture_output=True, text=True).stdout.strip()
            git("init", "-b", "qa")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "--allow-empty", "-m", "first")
            first = resolve_target(directory, "refs/heads/qa", "qa-server")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "--allow-empty", "-m", "second")
            second = resolve_target(directory, "refs/heads/qa", "qa-server")
            self.assertNotEqual(first["commit_sha"], second["commit_sha"])
            self.assertEqual(first["verification"], "not_verified_in_unity")
            self.assertEqual(git("branch", "--show-current"), "qa")
            self.assertEqual(git("status", "--porcelain"), "")
            with self.assertRaises(ValueError):
                resolve_target(directory, "--output=bad", "qa-server")
            with self.assertRaises(ValueError):
                resolve_target(directory, "main", "qa-server")


class ProvisionAdapterTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.factory = Mock()
        self.factory.return_value.__enter__ = Mock(return_value=self.client)
        self.factory.return_value.__exit__ = Mock(return_value=False)
        self.bridge = CodexBridge({"thread_id":"legacy", "project_id":"project",
            "project_path":str(Path.cwd())}, self.factory)

    def test_project_is_discovered_and_git_defaults_to_worktree(self):
        self.client.tool.return_value = {"projects":[{"projectId":"project", "hostId":"local",
            "path":str(Path.cwd()), "isGitRepository":True}]}
        self.assertEqual(self.bridge.session_target()["environment"], {"type":"worktree"})
        self.client.tool.assert_called_once_with("list_projects", {})

    def test_create_separates_bootstrap_from_linear_message(self):
        self.client.tool.return_value = {"clientThreadId":"pending"}
        self.assertEqual(self.bridge.create_session("token", {"type":"project"}), {"client_thread_id":"pending"})
        args = self.client.tool.call_args.args[1]
        self.assertIn(binding_marker("token"), args["prompt"])
        self.assertIn("do not call tools", args["prompt"])
        self.assertNotIn("model", args)

    def test_recovery_uses_actual_ids_and_input_marker_not_task_title_or_final(self):
        self.client.tool.return_value = {"threads":[
            {"id":"actual", "kind":"codex", "hostId":"local", "projectId":"project", "title":"FarmQA session token"}]}
        child = Mock()
        self.bridge.for_thread = Mock(return_value=child)
        child.read.return_value = {"turns":[{"status":"completed", "items":[
            {"type":"agentMessage", "text":binding_marker("token")},
            {"type":"userMessage", "content":[{"type":"text", "text":"quoted "+binding_marker("token")}]}]}]}
        self.assertIsNone(self.bridge.find_session("token"))
        child.read.return_value["turns"][0]["items"][1]["content"][0]["text"] = binding_marker("token")+"\nInitialize only"
        self.assertEqual(self.bridge.find_session("token"), "actual")
        self.bridge.for_thread.assert_called_with("actual")

    def test_multiple_binding_matches_fail_closed(self):
        self.client.tool.return_value = {"threads":[
            {"id":task, "kind":"codex", "hostId":"local", "projectId":"project", "title":"FarmQA session token"} for task in ("a","b")]}
        child = Mock()
        child.read.return_value = {"turns":[{"items":[{"type":"userMessage", "content":[
            {"type":"text", "text":binding_marker("token")}]}]}]}
        self.bridge.for_thread = Mock(return_value=child)
        with self.assertRaises(AppProtocolError):
            self.bridge.find_session("token")

    def test_read_rejects_response_for_another_task(self):
        self.client.tool.return_value = {"thread":{"id":"wrong-task"}}
        with self.assertRaises(AppProtocolError):
            self.bridge.read()

    def test_live_delegation_envelope_matches_first_input_line(self):
        child = Mock()
        child.read.return_value = {"turns":[{"status":"completed", "items":[{
            "type":"functionCallOutput", "namespace":"codex_app", "name":"create_thread",
            "output":{"text":"<codex_delegation>\n  <source_thread_id>owner</source_thread_id>\n  <input>"
                +binding_marker("token")+"\nInitialize only.</input>\n</codex_delegation>"}}]}]}
        self.bridge.for_thread = Mock(return_value=child)
        self.assertTrue(self.bridge.session_initialized("actual", "token"))
        self.assertFalse(self.bridge.session_initialized("actual", "different"))

    def test_worktree_missing_from_app_list_uses_readonly_metadata_then_verifies_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"state.sqlite"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE threads(id TEXT,name TEXT,archived INT,created_at INT)")
                db.execute("INSERT INTO threads VALUES ('actual','FarmQA session token',0,1)")
            self.bridge.config["state_db_path"] = str(path)
            self.client.tool.return_value = {"threads":[]}
            child = Mock()
            child.read.return_value = {"turns":[]}
            self.bridge.for_thread = Mock(return_value=child)
            self.assertIsNone(self.bridge.find_session("token"))
            child.read.return_value = {"turns":[{"status":"completed", "items":[{
                "type":"userMessage", "content":[{"type":"text", "text":binding_marker("token")}]}]}]}
            self.assertEqual(self.bridge.find_session("token"), "actual")
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM threads").fetchone()[0], 1)

    def test_rebind_preserves_routing_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"codex.json"
            runtime = Path(directory)/"runtime"
            runtime.touch()
            path.write_text(json.dumps({"thread_id":"legacy", "server_path":str(runtime),
                "session_routing":True, "project_id":"project", "project_path":directory}))
            with patch.dict(os.environ, {"CODEX_THREAD_ID":"owner", "CODEX_APP_TOOLS_PIPE_PATH":"pipe",
                                         "CODEX_MCP_NODE_PATH":str(runtime)}), patch.object(CodexBridge, "read",
                                         return_value={"thread":{"id":"legacy"}}):
                configure(path, None, None, rebind=True)
            config = json.loads(path.read_text())
            self.assertTrue(config["session_routing"])
            self.assertEqual(config["project_id"], "project")


if __name__ == "__main__":
    unittest.main()
