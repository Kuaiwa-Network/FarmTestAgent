"""Offline security and delivery tests; no calls to the real Linear API."""
import hashlib
import hmac
import io
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from unittest.mock import Mock

SPEC = importlib.util.spec_from_file_location(
    "farmqa", Path(__file__).parents[1] / "tools" / "linear_farmqa.py")
farmqa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(farmqa)


class FarmQATest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "events.sqlite3"
        self.send = Mock(return_value={"success": True, "agentActivity": {"id": "out"}})
        self.service = farmqa.Service(self.db, "signing-secret", "client", "app", "org", self.send)
        self.addCleanup(self.service.close)

    def event(self, **changes):
        result = {"type": "AgentSessionEvent", "action": "created",
                  "webhookTimestamp": 100_000, "organizationId": "org",
                  "oauthClientId": "client", "appUserId": "app",
                  "agentSession": {"id": "session"}}
        result.update(changes)
        return result

    def receive(self, event=None, signature=None):
        body = json.dumps(event or self.event()).encode()
        signature = signature if signature is not None else hmac.new(
            b"signing-secret", body, hashlib.sha256).hexdigest()
        return self.service.receive(body, signature, now_ms=100_000)

    def test_mention_produces_one_final_reply(self):
        self.assertEqual(self.receive(), (200, "accepted"))
        self.assertTrue(self.service.process_one())
        sent = self.send.call_args.args[0]
        self.assertEqual(sent["agentSessionId"], "session")
        self.assertEqual(sent["content"]["type"], "response")
        self.assertIn("FarmQA is connected", sent["content"]["body"])
        self.assertEqual(self.service.results()[0]["status"], "sent")

    def test_duplicate_delivery_and_restart_do_not_repeat_reply(self):
        self.receive()
        self.service.process_one()
        self.assertEqual(self.receive(), (200, "duplicate"))
        self.service.close()
        self.service = farmqa.Service(self.db, "signing-secret", "client", "app", "org", self.send)
        self.addCleanup(self.service.close)
        self.assertEqual(self.receive(), (200, "duplicate"))
        self.assertFalse(self.service.process_one())
        self.assertEqual(self.send.call_count, 1)

    def test_followup_gets_its_own_reply_but_duplicate_does_not(self):
        self.receive()
        event = self.event(action="prompted", agentActivity={"id": "prompt1", "agentSessionId": "session", "content": {"type": "prompt", "body": "hello again"}})
        self.assertEqual(self.receive(event), (200, "accepted"))
        self.assertEqual(self.receive(event), (200, "duplicate"))
        self.service.process_one()
        self.service.process_one()
        self.assertEqual(self.send.call_count, 2)

    def test_bad_signatures_stale_and_wrong_identity_never_send(self):
        for signature in ["", "abc", "0" * 64]:
            self.assertEqual(self.receive(signature=signature)[0], 401)
        for changes in [{"webhookTimestamp": 0}, {"webhookTimestamp": 200_000},
                        {"webhookTimestamp": "100000"}, {"appUserId": "other"},
                        {"oauthClientId": "other"}, {"organizationId": "other"}]:
            with self.subTest(changes=changes):
                self.assertIn(self.receive(self.event(**changes))[0], (400, 401, 403))
        self.assertFalse(self.service.process_one())
        self.send.assert_not_called()

    def test_malformed_event_and_non_prompt_are_not_replies(self):
        self.assertEqual(self.receive(self.event(agentSession={}))[0], 400)
        self.assertEqual(self.receive(self.event(action="prompted"))[0], 400)
        self.assertEqual(self.receive(self.event(action="prompted", agentActivity={"id":"x", "content":{"type":"response"}})), (200, "ignored"))
        self.assertEqual(self.receive(self.event(type="Comment")), (200, "ignored"))
        self.assertEqual(self.receive(self.event(action="updated")), (200, "ignored"))
        self.assertFalse(self.service.process_one())

    def test_failed_delivery_is_visible_not_success_or_silent_retry(self):
        self.send.side_effect = TimeoutError("potentially sensitive remote detail")
        self.receive()
        self.service.process_one()
        result = self.service.results()[0]
        self.assertEqual(result["status"], "uncertain")
        self.assertEqual(result["error"], "TimeoutError")
        self.assertFalse(self.service.process_one())
        self.assertEqual(self.receive(), (200, "duplicate"))
        self.assertEqual(self.send.call_count, 1)

    def test_false_api_success_is_not_sent(self):
        self.send.return_value = {"success": False}
        self.receive()
        self.service.process_one()
        self.assertEqual(self.service.results()[0]["status"], "uncertain")

    def test_pending_event_survives_restart_without_storing_prompt(self):
        self.receive(self.event(promptContext="PRIVATE ISSUE CONTENT"))
        self.service.close()
        self.service = farmqa.Service(self.db, "signing-secret", "client", "app", "org", self.send)
        self.addCleanup(self.service.close)
        self.assertTrue(self.service.process_one())
        self.assertNotIn(b"PRIVATE ISSUE CONTENT", self.db.read_bytes())

    def test_interrupted_send_is_not_retried_after_restart(self):
        self.receive()
        with self.service.db:
            self.service.db.execute("UPDATE events SET status='sending'")
        self.service.close()
        self.service = farmqa.Service(self.db, "signing-secret", "client", "app", "org", self.send)
        self.addCleanup(self.service.close)
        self.assertFalse(self.service.process_one())
        self.assertEqual(self.service.results()[0]["status"], "uncertain")

    def test_http_route_accepts_signed_event_and_rejects_unsigned(self):
        server = farmqa.make_server(self.service, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join()
        self.addCleanup(cleanup)
        url = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(url + "/health") as response:
            self.assertEqual(response.status, 200)
        raw = json.dumps(self.event(webhookTimestamp=int(time.time()*1000))).encode()
        signature = hmac.new(b"signing-secret", raw, hashlib.sha256).hexdigest()
        request = urllib.request.Request(url + "/webhook", data=raw, headers={"Linear-Signature": signature})
        with urllib.request.urlopen(request) as response:
            self.assertEqual(json.load(response), {"status": "accepted"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(urllib.request.Request(url + "/webhook", data=raw))
        self.assertEqual(caught.exception.code, 401)
        caught.exception.close()
        self.assertTrue(self.service.process_one())
        self.send.assert_called_once()

    def test_second_receiver_cannot_bind_the_same_port(self):
        server = farmqa.make_server(self.service, port=0)
        self.addCleanup(server.server_close)
        with self.assertRaises(OSError):
            other = farmqa.make_server(self.service, port=server.server_port)
            self.addCleanup(other.server_close)

    def test_linear_api_uses_app_token_and_checks_graphql_success(self):
        transport = Mock(side_effect=[io.BytesIO(json.dumps({"access_token": "fake-token", "expires_in": 600}).encode()),
                                      io.BytesIO(json.dumps({"data": {"agentActivityCreate": {"success": True, "agentActivity": {"id": "a"}}}}).encode())])
        api = farmqa.LinearAPI("client", "client-secret", request=transport)
        result = api.send({"agentSessionId": "session", "content": {"type": "response", "body": farmqa.REPLY}})
        self.assertTrue(result["success"])
        token_request = transport.call_args_list[0].args[0]
        self.assertIn(b"grant_type=client_credentials", token_request.data)
        mutation_request = transport.call_args_list[1].args[0]
        self.assertEqual(mutation_request.get_header("Authorization"), "Bearer fake-token")
        self.assertEqual(json.loads(mutation_request.data)["variables"]["input"]["content"]["body"], farmqa.REPLY)

    def test_graphql_errors_are_not_success_even_on_http_200(self):
        transport = Mock(return_value=io.BytesIO(b'{"errors":[{"message":"not permitted"}]}'))
        api = farmqa.LinearAPI("client", "secret", request=transport)
        api.token, api.expires = "fake-token", time.time() + 60
        with self.assertRaises(RuntimeError):
            api.send({})


if __name__ == "__main__":
    unittest.main()
