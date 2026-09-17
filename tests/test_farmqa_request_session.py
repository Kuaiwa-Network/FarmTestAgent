"""Request/session diagnostics use real reservations and controlled Unity reads."""
import copy
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import runpy
import time
import unittest
from unittest.mock import patch

import test_farmqa_controller as helpers


class RequestSessionTests(unittest.TestCase):
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
        self.assertIsNotNone(importlib.util.find_spec('farmqa_request_session'),
                             'Request-bound session diagnostic is missing')
        from farmqa_request_session import RequestSessionInspector
        self.request = self.queue()
        self.owner = self.acquire()
        self.expected = {'instance':'Farm@abc', 'build_target':'StandaloneWindows64',
                         'hot_mvid':'11111111-1111-1111-1111-111111111111',
                         'server_environment':'fixture', 'player_id':42, 'route_sha256':'b'*64}
        self.remote = SessionRemote(self.target['repository'])
        self.inspector = RequestSessionInspector(self.service.controller, self.remote)
        self.source = {'commit_sha':'a'*40, 'dirty':[], 'index_sha256':'c'*64}
        self.snapshot = patch('farmqa_request_session.source_snapshot', return_value=self.source).start()
        self.addCleanup(patch.stopall)

    def bind(self, **overrides):
        self.inspector.bind(self.request, self.owner['token'], {**self.expected, **overrides})

    def inspect(self):
        return self.inspector.inspect(self.request, self.owner['token'])

    def stop(self):
        self.receive(self.stop_event(createdAt='2026-09-17T01:00:01Z'))

    def test_match_is_recorded_but_never_enables_execution(self):
        self.bind()
        result = self.inspect()
        self.assertEqual(result['request_session_match'], 'match')
        self.assertEqual(result['verdict'], 'BLOCKED')
        self.assertIs(result['execution_enabled'], False)
        recorded = self.service.db.execute('SELECT result_json FROM controller_session_observations').fetchone()[0]
        self.assertEqual(json.loads(recorded), result)
        self.assertEqual(self.service.controller.status()[0]['state'], 'active')
        self.assertEqual(self.service.db.execute('SELECT count(*) FROM controller_actions').fetchone()[0], 0)

    def test_binding_is_immutable_across_reconstruction(self):
        self.bind()
        from farmqa_request_session import RequestSessionInspector
        self.inspector = RequestSessionInspector(self.service.controller, self.remote)
        self.bind()  # Exact repeat is idempotent.
        with self.assertRaises(ValueError): self.bind(player_id=43)
        self.assertEqual(self.inspect()['request_session_match'], 'match')

    def test_wrong_owner_queued_and_stopped_requests_do_not_read_unity(self):
        self.bind()
        with self.assertRaises(ValueError): self.inspector.inspect(self.request, 'wrong')
        queued = self.queue(session='second', activity='two')
        with self.assertRaises(ValueError): self.inspector.bind(queued, 'wrong', self.expected)
        self.stop()
        with self.assertRaises(ValueError): self.inspect()
        self.assertEqual(self.remote.calls, [])

    def test_stop_during_read_does_not_hold_database_lock_or_validate_request(self):
        self.bind()
        def stop_elsewhere():
            with closing(sqlite3.connect(self.db, timeout=0.1)) as db, db:
                db.execute("UPDATE controller_requests SET state='cancel_requested' WHERE request_id=?", (self.request,))
        self.remote.on_sample = stop_elsewhere
        result = self.inspect()
        self.assertEqual(result['checks']['session'], 'match')
        self.assertEqual(result['checks']['request_current'], 'mismatch')
        self.assertEqual(result['request_session_match'], 'unknown')
        self.assertEqual(self.service.controller.status()[0]['state'], 'cancel_requested')

    def test_released_owner_during_read_invalidates_sample(self):
        self.bind()
        def release():
            with self.service.db:
                self.service.controller.release(self.request, self.owner['token'])
        self.remote.on_sample = release
        self.assertEqual(self.inspect()['request_session_match'], 'unknown')
        with self.assertRaises(ValueError): self.inspect()

    def test_changed_target_during_read_invalidates_result(self):
        self.bind()
        def mutate():
            with self.service.db:
                self.service.db.execute("UPDATE controller_requests SET target_json='{}' WHERE request_id=?", (self.request,))
        self.remote.on_sample = mutate
        self.assertEqual(self.inspect()['checks']['request_current'], 'mismatch')

    def test_deleted_binding_during_read_invalidates_result(self):
        self.bind()
        def mutate():
            with self.service.db:
                self.service.db.execute('DELETE FROM controller_session_bindings WHERE request_id=?', (self.request,))
        self.remote.on_sample = mutate
        self.assertEqual(self.inspect()['checks']['request_current'], 'mismatch')

    def test_mismatched_environment_and_malformed_expectations_rejected_before_binding(self):
        for overrides in ({'server_environment':'production'}, {'player_id':True},
                          {'route_sha256':'wss://private'}, {'hot_mvid':'unknown'},
                          {'instance':''}, {'credential':'DO-NOT-PERSIST'}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError): self.bind(**overrides)
        self.assertEqual(self.remote.calls, [])

    def test_wrong_player_route_and_unavailable_samples_do_not_match(self):
        self.bind()
        for change in ({'player_id':43}, {'route_sha256':'c'*64}, {'authenticated':False},
                       {'transport_connected':False}, {'generation_after':8},
                       {'schema_version':True}, {'observed_at_ms':1}, {'status':'edit_mode'}):
            with self.subTest(change=change):
                self.remote.change = change
                self.assertEqual(self.inspect()['request_session_match'], 'unknown')

    def test_module_project_platform_source_and_busy_mismatch_block(self):
        self.bind()
        for field, value in [('buildTarget','Android'), ('dataPath',str(Path(self.temp.name)/'other')),
                             ('assemblies',[]), ('isCompiling',True)]:
            with self.subTest(field=field):
                self.remote.editor_change = {field:value}
                self.assertEqual(self.inspect()['request_session_match'], 'unknown')
        self.remote.editor_change = {}
        self.source['dirty'] = [{'path':'changed.cs'}]
        self.assertEqual(self.inspect()['checks']['source'], 'mismatch')
        self.source['dirty'] = []
        self.source['commit_sha'] = 'f'*40
        self.assertEqual(self.inspect()['checks']['source'], 'mismatch')

    def test_instance_or_source_change_after_sample_discards_match(self):
        self.bind()
        self.remote.on_sample = lambda: setattr(self.remote, 'instance', 'replacement')
        self.assertEqual(self.inspect()['request_session_match'], 'unknown')
        self.remote.instance = 'Farm@abc'
        self.remote.on_sample = lambda: None
        self.snapshot.side_effect = [copy.deepcopy(self.source), {**self.source, 'index_sha256':'d'*64}]
        self.assertEqual(self.inspect()['checks']['source'], 'mismatch')

    def test_post_sample_delay_expires_before_database_append(self):
        self.bind()
        self.remote.change = {'observed_at_ms':1000}
        with patch('farmqa_session_identity.time.time', return_value=1) as clock:
            original_snapshot = self.snapshot.return_value
            def post_read_delay(_):
                if self.remote.calls:
                    clock.return_value = 20
                return original_snapshot
            self.snapshot.side_effect = post_read_delay
            self.assertEqual(self.inspect()['request_session_match'], 'unknown')

    def test_errors_and_extra_remote_fields_are_redacted(self):
        self.bind()
        self.remote.change = {'credential':'DO-NOT-PERSIST'}
        result = self.inspect()
        self.assertNotIn('DO-NOT-PERSIST', json.dumps(result))
        def fail(): raise RuntimeError('DO-NOT-PERSIST')
        self.remote.on_sample = fail
        result = self.inspect()
        self.assertEqual(result['error_type'], 'RuntimeError')
        self.assertEqual(result['request_session_match'], 'unknown')
        saved = ''.join(row[0] for row in self.service.db.execute('SELECT result_json FROM controller_session_observations'))
        self.assertNotIn('DO-NOT-PERSIST', saved)

    def test_outer_transaction_and_unbound_request_are_rejected(self):
        with self.assertRaises(ValueError): self.inspect()
        self.bind()
        with self.service.db:
            self.service.db.execute('BEGIN IMMEDIATE')
            with self.assertRaises(ValueError): self.inspect()
        self.assertEqual(self.remote.calls, [])


class SessionRemote:
    def __init__(self, project):
        self.project, self.instance = project, 'Farm@abc'
        self.calls, self.change, self.editor_change = [], {}, {}
        self.on_sample = lambda: None

    def read(self, uri):
        self.calls.append(uri)
        return {'mcpforunity://custom-tools':{},
                'mcpforunity://instances':{'instances':[{'id':self.instance}]},
                'mcpforunity://project/info':{'projectRoot':self.project, 'platform':'StandaloneWindows64'},
                'mcpforunity://editor/state':{'tests':{'is_running':False}}}[uri]

    def select(self, instance):
        if instance != self.instance: raise ValueError('Wrong instance')

    def probe(self):
        return {'dataPath':str(Path(self.project)/'Assets'), 'buildTarget':'StandaloneWindows64',
                'isPlaying':True, 'isPlayingOrWillChangePlaymode':True,
                'isCompiling':False, 'isUpdating':False,
                'assemblies':[{'name':'HotUpdate', 'moduleMvid':'11111111-1111-1111-1111-111111111111'}],
                **self.editor_change}

    def session_probe(self):
        self.on_sample()
        return {'schema_version':1, 'status':'observed', 'observed_at_ms':time.time()*1000,
                'is_playing':True, 'authenticated':True, 'transport_connected':True,
                'objects_stable':True, 'generation_before':3, 'generation_after':3,
                'player_id':42, 'route_sha256':'b'*64, **self.change}


class ReplayAssertionTests(unittest.TestCase):
    def setUp(self):
        namespace = runpy.run_path(str(Path(__file__).parent/'probes/run_request_session.py'))
        self.assertIn('check_case', namespace, 'Replay needs cause-specific assertions')
        self.check_case = namespace['check_case']
        self.checks = {'source':'match', 'editor':'match', 'session':'mismatch', 'request_current':'match'}
        self.result = {'checks':dict(self.checks), 'request_session_match':'unknown',
                       'verdict':'BLOCKED', 'execution_enabled':False}

    def test_expected_mismatch_passes_but_unrelated_failure_does_not(self):
        self.check_case(self.result, self.checks)
        for field in self.checks:
            altered = copy.deepcopy(self.result)
            altered['checks'][field] = 'unknown'
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.check_case(altered, self.checks)

    def test_replay_rejects_execution_enabled_or_inconsistent_aggregate(self):
        for key, value in [('execution_enabled',True), ('execution_enabled',0),
                           ('verdict','PASS'), ('request_session_match','match')]:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.check_case({**self.result,key:value}, self.checks)
