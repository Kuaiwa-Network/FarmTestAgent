import json
import time
import unittest

import test_farmqa_controller as helpers
from farmqa_fixture_adapter import FixtureAdapter


class RemoteFixture:
    """Controlled transport outcomes; real Unity behavior is a separate live test."""
    def __init__(self):
        self.calls = []
        self.rows = {}
        self.lose = None
        self.lose_before = None
        self.valid = True
        self.transform = lambda x: x

    def validate(self, binding):
        self.calls.append('validate')
        if not self.valid:
            raise ValueError('Wrong actual target')

    def exchange(self, op, action_id, binding):
        self.calls.append(op)
        if self.lose_before == op:
            self.lose_before = None
            raise TimeoutError('Transport failed BEFORE dispatch')
        if action_id not in self.rows:
            if op not in ('start', 'cancel'):
                raise ValueError('Unknown remote action')
            self.rows[action_id] = {'started': op == 'start', 'completed': op == 'cancel',
                                   'quiescent': op == 'cancel', 'closed': False, 'cancel_requested': op == 'cancel'}
        row = self.rows[action_id]
        if op == 'cancel' and not row['closed']:
            row.update(cancel_requested=True, completed=True, quiescent=True)
        if op == 'close':
            if not row['completed'] or not row['quiescent']:
                raise ValueError('Still running')
            row['closed'] = True
        if self.lose == op:
            self.lose = None
            raise TimeoutError('Response lost AFTER dispatch')
        return self.transform({'schema_version': 1, 'action_id': action_id, 'run_id': binding['run_id'],
            'observed_at_ms': int(time.time()*1000), **row,
            'events': ['down', 'up'] if row['completed'] and row['started'] else [],
            'success': None, 'new_console_errors': 0})


class FixtureAdapterTests(unittest.TestCase):
    setUpBase = helpers.ControllerQueueTests.setUp
    open_service = helpers.ControllerQueueTests.open_service
    receive = helpers.ControllerQueueTests.receive
    event = helpers.ControllerQueueTests.event
    stop_event = helpers.ControllerQueueTests.stop_event
    accept = helpers.ControllerQueueTests.accept
    queue = helpers.ControllerQueueTests.queue
    acquire = helpers.ControllerQueueTests.acquire

    def setUp(self):
        self.setUpBase()
        self.target['server_environment'] = 'offline-login-fixture'
        self.request = self.queue()
        self.owner = self.acquire()
        self.remote = RemoteFixture()
        self.adapter = FixtureAdapter(self.service.controller, self.remote)
        self.binding = {'instance': 'Farm@abc', 'project': self.target['repository'],
                        'commit_sha': 'a'*40, 'hot_mvid': '11111111-1111-1111-1111-111111111111',
                        'build_target': 'StandaloneWindows64', 'run_id': 'b'*32}

    def start(self):
        return self.adapter.start(self.request, self.owner['token'], self.binding)

    def stop(self):
        self.receive(self.stop_event(createdAt='2026-09-17T01:00:01Z'))

    def test_start_persists_and_release_waits_for_remote_close(self):
        self.start()
        with self.service.db, self.assertRaises(ValueError):
            self.service.controller.release(self.request, self.owner['token'])
        with self.assertRaises(ValueError):
            self.adapter.finish(self.request, self.owner['token'])
        self.stop()
        self.assertTrue(self.adapter.observe(self.request, self.owner['token'])['cancel_requested'])
        self.assertEqual(self.adapter.finish(self.request, self.owner['token'])['reservation_state'], 'cancelled')

    def test_wrong_token_and_retired_owner_never_reach_transport(self):
        with self.assertRaises(ValueError):
            self.adapter.start(self.request, 'wrong', self.binding)
        self.assertEqual(self.remote.calls, [])
        self.start(); self.stop(); self.adapter.finish(self.request, self.owner['token'])
        calls = list(self.remote.calls)
        for method in (self.adapter.observe, self.adapter.finish):
            with self.assertRaises(ValueError):
                method(self.request, self.owner['token'])
        with self.assertRaises(ValueError):
            self.start()
        self.assertEqual(self.remote.calls, calls)

    def test_lost_start_response_is_never_retried_and_blocks_successor(self):
        second = self.queue(session='second', activity='two')
        self.remote.lose = 'start'
        with self.assertRaises(TimeoutError): self.start()
        self.assertIsNone(self.acquire('competitor'))
        with self.assertRaises(ValueError): self.start()
        self.assertEqual(self.remote.calls.count('start'), 1)
        # A reconstructed adapter can inspect the persisted action, not re-dispatch it.
        self.adapter = FixtureAdapter(self.service.controller, self.remote)
        self.stop(); self.adapter.finish(self.request, self.owner['token'])
        self.assertEqual(self.acquire('successor')['request_id'], second)

    def test_lost_close_response_keeps_hold_until_matching_closed_observation(self):
        self.start(); self.stop(); self.adapter.observe(self.request, self.owner['token'])
        self.remote.lose = 'close'
        with self.assertRaises(TimeoutError): self.adapter.finish(self.request, self.owner['token'])
        self.assertIsNone(self.acquire('competitor'))
        self.assertEqual(self.adapter.finish(self.request, self.owner['token'])['reservation_state'], 'cancelled')
        self.assertEqual(self.remote.calls.count('start'), 1)

    def test_stop_before_start_and_target_mismatch_do_not_dispatch(self):
        for field, value in [('commit_sha', 'c'*40), ('project', self.target['repository']+'/different')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.adapter.start(self.request, self.owner['token'], {**self.binding, field:value})
        self.remote.valid = False
        with self.assertRaises(ValueError): self.start()
        self.remote.valid = True
        self.stop()
        with self.assertRaises(ValueError): self.start()
        self.assertNotIn('start', self.remote.calls)

    def test_malformed_stale_or_wrong_action_observation_never_unlocks(self):
        self.start(); self.stop()
        for change in ({'schema_version':True}, {'action_id':'wrong'}, {'run_id':'wrong'}, {'observed_at_ms':0},
                       {'quiescent':1}, {'completed':None}, {'closed':'true'}):
            self.remote.transform = lambda x, change=change: {**x, **change}
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.adapter.finish(self.request, self.owner['token'])
            with self.service.db, self.assertRaises(ValueError):
                self.service.controller.release(self.request, self.owner['token'])

    def test_missing_remote_state_after_reload_never_unlocks(self):
        self.start(); self.remote.rows.clear()
        with self.assertRaises(ValueError): self.adapter.observe(self.request, self.owner['token'])
        self.assertIsNone(self.acquire('competitor'))

    def test_intent_is_committed_before_remote_dispatch(self):
        original = self.remote.exchange
        def inspect(op, action, binding):
            self.assertFalse(self.service.db.in_transaction)
            row = self.service.db.execute('SELECT * FROM controller_actions WHERE request_id=?', (self.request,)).fetchone()
            self.assertEqual(row['action_id'], action)
            return original(op, action, binding)
        self.remote.exchange = inspect
        self.start()

    def test_stop_after_intent_before_dispatch_fences_without_starting(self):
        original = self.adapter._exchange
        def stop_then_exchange(request, token, op):
            if op == 'start': self.stop()
            return original(request, token, op)
        self.adapter._exchange = stop_then_exchange
        value = self.start()
        self.assertFalse(value['started'])
        self.assertTrue(value['cancel_requested'])
        self.assertNotIn('start', self.remote.calls)

    def test_lost_cancel_response_holds_then_observes_without_restarting(self):
        self.start(); self.stop(); self.remote.lose = 'cancel'
        with self.assertRaises(TimeoutError): self.adapter.observe(self.request, self.owner['token'])
        self.assertIsNone(self.acquire('competitor'))
        self.assertEqual(self.adapter.finish(self.request, self.owner['token'])['reservation_state'], 'cancelled')
        self.assertEqual(self.remote.calls.count('start'), 1)
        self.assertEqual(self.remote.calls.count('cancel'), 2)

    def test_cancel_not_delivered_is_reconciled_with_exact_action_retry(self):
        self.start(); self.stop(); self.remote.lose_before = 'cancel'
        with self.assertRaises(TimeoutError): self.adapter.observe(self.request, self.owner['token'])
        self.assertIsNone(self.acquire('competitor'))
        value = self.adapter.observe(self.request, self.owner['token'])
        self.assertTrue(value['cancel_requested'])
        self.assertEqual(self.remote.calls.count('cancel'), 2)
        self.assertEqual(self.remote.calls.count('start'), 1)

    def test_rejected_binding_does_not_reach_transport(self):
        for patch in ({'run_id':'not-hex'}, {'build_target':'Android'}, {'hot_mvid':'unknown'}, {'code':'injection'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                self.adapter.start(self.request, self.owner['token'], {**self.binding, **patch})
        self.assertEqual(self.remote.calls, [])

    def test_action_observations_do_not_persist_extra_remote_fields(self):
        self.remote.transform = lambda x: {**x, 'token':'must-not-be-persisted'}
        self.assertNotIn('token', self.start())
        row = self.service.db.execute('SELECT observation_json FROM controller_actions').fetchone()
        self.assertNotIn('must-not-be-persisted', row[0])


if __name__ == '__main__':
    unittest.main()
