import importlib.util
import unittest

import test_farmqa_fixture_adapter as helpers
from farmqa_request_session import RequestSessionInspector


class AuthenticatedFixtureTests(unittest.TestCase):
    setUpBase = helpers.FixtureAdapterTests.setUpBase
    open_service = helpers.FixtureAdapterTests.open_service
    receive = helpers.FixtureAdapterTests.receive
    event = helpers.FixtureAdapterTests.event
    stop_event = helpers.FixtureAdapterTests.stop_event
    accept = helpers.FixtureAdapterTests.accept
    queue = helpers.FixtureAdapterTests.queue
    acquire = helpers.FixtureAdapterTests.acquire
    stop = helpers.FixtureAdapterTests.stop

    def setUp(self):
        self.setUpBase()
        self.assertIsNotNone(importlib.util.find_spec('farmqa_authenticated_fixture'),
                             'Authenticated fixture admission is not implemented')
        from farmqa_authenticated_fixture import AuthenticatedFixtureAdapter
        self.request = self.queue()
        self.owner = self.acquire()
        self.expected = {'instance':'Farm@abc', 'build_target':'StandaloneWindows64',
                         'hot_mvid':'11111111-1111-1111-1111-111111111111',
                         'server_environment':'fixture', 'player_id':42, 'route_sha256':'b'*64}
        self.binding = {**self.expected, 'project':self.target['repository'], 'commit_sha':'a'*40,
                        'run_id':'c'*32, 'generation':3}
        self.remote = helpers.RemoteFixture()
        self.remote.transform = lambda r: {**r,'admission':'accepted','session_lost':False}
        self.adapter = AuthenticatedFixtureAdapter(self.service.controller, self.remote)

    def bind(self):
        RequestSessionInspector(self.service.controller).bind(self.request,self.owner['token'],self.expected)

    def start(self):
        return self.adapter.start(self.request,self.owner['token'],self.binding)

    def test_start_requires_the_requests_independent_immutable_expectation(self):
        with self.assertRaises(ValueError): self.start()
        self.assertEqual(self.remote.calls, [])
        self.bind()
        self.binding['player_id'] = 43
        with self.assertRaises(ValueError): self.start()
        self.assertEqual(self.remote.calls, [])
        self.binding['player_id'] = 42
        result = self.start()
        self.assertEqual(result['admission'], 'accepted')
        self.assertIs(result['session_lost'], False)

    def test_target_or_binding_change_during_validation_does_not_record_action(self):
        self.bind()
        def validate(_):
            with self.service.db:
                self.service.db.execute('DELETE FROM controller_session_bindings WHERE request_id=?',(self.request,))
        self.remote.validate = validate
        with self.assertRaises(ValueError): self.start()
        self.assertEqual(self.service.db.execute('SELECT count(*) FROM controller_actions').fetchone()[0],0)

    def test_invalid_generation_and_extra_binding_fields_rejected_before_remote(self):
        self.bind()
        for generation in (0,True,-1,4294967296,'3'):
            self.binding['generation'] = generation
            with self.assertRaises(ValueError): self.start()
        self.binding['generation'] = 3
        self.binding['code'] = 'arbitrary'
        with self.assertRaises(ValueError): self.start()
        self.assertEqual(self.remote.calls, [])

    def test_rejected_session_is_unstarted_cancelled_then_closed_before_release(self):
        self.bind()
        def reject(r):
            self.remote.rows[r['action_id']].update(started=False,cancel_requested=True,completed=True,quiescent=True)
            return {**r,'started':False,'cancel_requested':True,'completed':True,'quiescent':True,
                    'admission':'session_rejected','session_lost':False}
        self.remote.transform = reject
        self.assertEqual(self.start()['admission'],'session_rejected')
        with self.service.db, self.assertRaises(ValueError):
            self.service.controller.release(self.request,self.owner['token'])
        self.assertEqual(self.adapter.finish(self.request,self.owner['token'])['reservation_state'],'released')

    def test_loss_of_session_does_not_block_exact_action_cancellation(self):
        self.bind();self.start()
        self.remote.transform = lambda r: {**r,'admission':'accepted','session_lost':True}
        self.stop()
        result = self.adapter.finish(self.request,self.owner['token'])
        self.assertEqual(result['reservation_state'],'cancelled')
        self.assertIs(result['session_lost'], True)
        self.assertIn('cancel',self.remote.calls)

    def test_unknown_or_inconsistent_admission_keeps_reservation_held(self):
        self.bind()
        self.remote.transform = lambda r: {**r,'admission':'session_rejected','session_lost':False}
        with self.assertRaises(ValueError): self.start()
        with self.service.db, self.assertRaises(ValueError):
            self.service.controller.release(self.request,self.owner['token'])
        row=self.service.db.execute('SELECT state FROM controller_actions').fetchone()
        self.assertEqual(row[0],'uncertain')

    def test_only_allowlisted_admission_fields_persist(self):
        self.bind()
        self.remote.transform=lambda r:{**r,'admission':'accepted','session_lost':False,'credential':'DO-NOT-PERSIST'}
        self.start()
        raw=self.service.db.execute('SELECT observation_json FROM controller_actions').fetchone()[0]
        self.assertNotIn('DO-NOT-PERSIST',raw)

    def test_lost_start_reply_never_retries_and_retired_owner_cannot_dispatch(self):
        self.bind();self.remote.lose='start'
        with self.assertRaises(TimeoutError): self.start()
        with self.assertRaises(ValueError): self.start()
        self.assertEqual(self.remote.calls.count('start'),1)
        self.stop();self.adapter.finish(self.request,self.owner['token'])
        before=list(self.remote.calls)
        with self.assertRaises(ValueError): self.adapter.observe(self.request,self.owner['token'])
        self.assertEqual(self.remote.calls,before)
