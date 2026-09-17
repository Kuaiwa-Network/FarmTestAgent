from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

import test_farmqa_codex as helpers


class ControllerQueueTests(unittest.TestCase):
    open_service = helpers.BridgeTests.open_service
    receive = helpers.BridgeTests.receive
    event = helpers.BridgeTests.event
    stop_event = helpers.BridgeTests.stop_event
    restart = helpers.BridgeTests.restart

    def setUp(self):
        helpers.BridgeTests.setUp(self)
        self.assertTrue(hasattr(self.service, 'controller'), 'Controller queue is not initialized')
        self.target = {'repository': str(Path(self.temp.name).resolve()),
                       'requested_ref': 'refs/heads/qa', 'commit_sha': 'a'*40,
                       'server_environment': 'fixture', 'selected_at': 1,
                       'source': 'local_operator', 'verification': 'not_verified_in_unity'}

    def accept(self, session='linear-session', activity='one', date='2026-09-17T01:00:00Z', pin=True):
        with self.service.db:
            self.service.sessions.ensure(session, 'desktop-task')
            self.service.sessions.set_target(session, self.target if pin else None)
        self.assertEqual(self.receive(self.event(action='prompted', agentSession={'id': session},
            agentActivity={'id': activity, 'createdAt': date,
                           'content': {'type': 'prompt', 'body': 'private fixture prompt'}}))[0], 200)
        return 'org:prompted:'+activity

    def queue(self, **kwargs):
        event = self.accept(**kwargs)
        with self.service.db:
            return self.service.controller.enqueue(event)

    def acquire(self, owner='worker'):
        with self.service.db:
            return self.service.controller.acquire(owner)

    def test_no_automatic_enqueue_and_missing_target_rejected(self):
        key = self.accept(pin=False)
        self.assertEqual(self.service.controller.status(), [])
        with self.service.db, self.assertRaises(ValueError):
            self.service.controller.enqueue(key)
        self.bridge.dispatch.assert_not_called()

    def test_fifo_single_slot_and_idempotent_enqueue(self):
        a = self.queue()
        b = self.queue(session='b', activity='two')
        with self.service.db:
            self.assertEqual(self.service.controller.enqueue('org:prompted:one'), a)
        first = self.acquire()
        self.assertEqual(first['request_id'], a)
        self.assertIsNone(self.acquire('other'))
        with self.service.db:
            self.assertEqual(self.service.controller.release(a, first['token']), 'released')
        self.assertEqual(self.acquire()['request_id'], b)

    def test_target_snapshot_is_from_event_not_latest_session_selection(self):
        key = self.accept()
        with self.service.db:
            self.service.sessions.set_target('linear-session', {**self.target, 'commit_sha': 'b'*40})
            self.service.controller.enqueue(key)
        self.assertEqual(self.acquire()['target']['commit_sha'], 'a'*40)

    def test_stop_cancels_queue_retains_active_slot_and_other_session(self):
        a = self.queue()
        active = self.acquire()
        queued = self.queue(activity='two')
        b = self.queue(session='b', activity='three')
        self.receive(self.stop_event(createdAt='2026-09-17T01:00:01Z'))
        states = {r['request_id']: r['state'] for r in self.service.controller.status()}
        self.assertEqual(states, {a: 'cancel_requested', queued: 'cancelled', b: 'queued'})
        self.assertTrue(self.service.controller.cancelled(a, active['token']))
        self.assertIsNone(self.acquire('other'))
        with self.service.db:
            self.assertEqual(self.service.controller.release(a, active['token']), 'cancelled')
        self.assertEqual(self.acquire()['request_id'], b)

    def test_stop_cutoff_and_duplicate_leave_newer_request_queued(self):
        self.queue()
        stop = self.stop_event(createdAt='2026-09-17T01:00:01Z')
        self.receive(stop)
        newer = self.queue(activity='newer', date='2026-09-17T01:00:02Z')
        self.assertEqual(self.receive(stop), (200, 'duplicate'))
        self.assertEqual(self.acquire()['request_id'], newer)

    def test_stop_blocks_late_promotion_even_after_chat_reply_was_sent(self):
        key = self.accept()
        with self.service.db:
            self.service.db.execute("UPDATE events SET status='sent' WHERE event_key=?", (key,))
        self.receive(self.stop_event(createdAt='2026-09-17T01:00:01Z'))
        with self.service.db, self.assertRaises(ValueError):
            self.service.controller.enqueue(key)

    def test_restart_does_not_reclaim_active_reservation(self):
        a = self.queue()
        active = self.acquire()
        self.restart()
        self.assertIsNone(self.acquire('new-process'))
        with self.service.db:
            self.assertEqual(self.service.controller.release(a, active['token']), 'released')
            self.assertEqual(self.service.controller.release(a, active['token']), 'released')

    def test_wrong_token_cannot_release_or_read_owner_cancel_state(self):
        a = self.queue()
        self.acquire()
        for method in (self.service.controller.release, self.service.controller.cancelled):
            with self.service.db, self.assertRaises(ValueError):
                method(a, 'wrong-token')
        self.assertIsNone(self.acquire('other'))

    def test_unsigned_or_wrong_workspace_stop_cannot_cancel_controller(self):
        self.queue()
        self.assertEqual(self.service.receive(json.dumps(self.stop_event()).encode(), 'bad')[0], 401)
        stop = self.stop_event(); stop['organizationId'] = 'wrong'
        self.assertEqual(self.receive(stop)[0], 403)
        self.assertEqual(self.service.controller.status()[0]['state'], 'queued')

    def test_status_does_not_disclose_token_or_prompt(self):
        self.queue(); active = self.acquire()
        status = json.dumps(self.service.controller.status())
        self.assertNotIn(active['token'], status)
        self.assertNotIn('token', status)
        self.assertNotIn('private fixture prompt', status)

    def test_controller_stop_is_scoped_to_organization(self):
        self.queue()
        with self.service.db:
            self.service.controller.stop('other-org', 'linear-session', 9999999999999)
        self.assertEqual(self.service.controller.status()[0]['state'], 'queued')

    def test_autocommit_worker_cannot_acquire_without_explicit_transaction(self):
        from farmqa_controller import ControllerStore
        self.queue()
        with closing(sqlite3.connect(self.db,isolation_level=None)) as db:
            db.row_factory=sqlite3.Row
            store=ControllerStore(db)
            with self.assertRaises(ValueError):
                store.acquire('unsafe-worker')
            db.execute('BEGIN IMMEDIATE')
            self.assertIsNotNone(store.acquire('transactional-worker'))
            db.rollback()

    def test_cli_status_is_readonly_and_enqueue_is_explicit(self):
        key = self.accept()
        script = str(Path(__file__).resolve().parents[1]/'tools/farmqa_controller.py')
        def cli(*args):
            result = subprocess.run([sys.executable,script,*args,'--db',str(self.db)],
                                    capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            return json.loads(result.stdout)
        self.assertEqual(cli('status')['requests'], [])
        result = cli('enqueue','--event',key)
        self.assertFalse(result['execution_enabled'])
        self.assertEqual(len(result['requests']),1)
        self.assertEqual(cli('status')['requests'][0]['state'],'queued')

    def test_malformed_target_and_unknown_event_are_rejected(self):
        key = self.accept()
        for target in (None, {}, {**self.target,'commit_sha':'main'},
                       {**self.target,'server_environment':'x\nsecret'}):
            with self.subTest(target=target), self.service.db:
                self.service.db.execute('UPDATE bridge_jobs SET target_json=? WHERE event_key=?',
                                        (json.dumps(target),key))
                with self.assertRaises(ValueError):
                    self.service.controller.enqueue(key)
        with self.service.db, self.assertRaises(ValueError):
            self.service.controller.enqueue('org:prompted:missing')

    def test_two_processes_only_one_reserves(self):
        self.queue(); self.queue(session='b', activity='two')
        script = """import sys,sqlite3
from contextlib import closing
from farmqa_controller import ControllerStore
with closing(sqlite3.connect(sys.argv[1],timeout=5)) as db:
 db.row_factory=sqlite3.Row
 with db:
  result=ControllerStore(db).acquire('process')
 print(result['request_id'] if result else 'none')
"""
        tools = str(Path(__file__).resolve().parents[1]/'tools')
        processes = [subprocess.Popen([sys.executable, '-c', script, str(self.db)],
                                     cwd=tools, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for _ in range(2)]
        outputs = [p.communicate(timeout=10) for p in processes]
        for p, output in zip(processes, outputs):
            self.assertEqual(p.returncode, 0, output[1])
        self.assertEqual(sum(out[0].strip() != 'none' for out in outputs), 1)


if __name__ == '__main__':
    unittest.main()
