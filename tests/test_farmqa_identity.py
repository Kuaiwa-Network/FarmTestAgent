"""Identity diagnostics must not turn missing evidence into a game permit."""
import copy
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import unittest

import test_farmqa_controller as fixtures


class EditorFixture:
    """Only the external Unity boundary is replaced; Git and the ledger are real."""
    def __init__(self, root):
        self.root = str(root)
        self.instance = 'Farm-Client@fixture'
        self.after_read = None
        self.state = {
            'schema_version': 'unity-mcp/editor_state@2',
            'observed_at_unix_ms': time.time()*1000,
            'unity': {'instance_id': self.instance, 'unity_version': '2022.3.62f3',
                      'platform': 'WindowsEditor'},
            'editor': {'play_mode': {'is_playing': False, 'is_paused': False,
                                   'is_changing': False}},
            'compilation': {'is_compiling': False, 'is_domain_reload_pending': False},
            'assets': {'is_updating': False}, 'tests': {'is_running': False},
            'advice': {'ready_for_tools': True},
            'staleness': {'is_stale': False},
        }
        self.probe_result = {
            'isPlaying': False, 'isPlayingOrWillChangePlaymode': False,
            'isCompiling': False, 'isUpdating': False,
            'unityVersion': '2022.3.62f3', 'platform': 'WindowsEditor',
            'buildTarget': 'StandaloneWindows64', 'dataPath': str(root/'Assets'),
            'scene': {'isDirty': False},
            'assemblies': [{'name': name, 'moduleMvid': '58847d20-a524-43d9-b9da-3e2c9a1bc5ec'}
                           for name in ('HotUpdate', 'AOTScripts', 'Nova.Runtime', 'MCPForUnity.Editor')],
        }

    def read(self, uri):
        if uri.endswith('/custom-tools'):
            return {'success': True}
        if uri.endswith('/instances'):
            return {'success': True, 'instances': [{'id': self.instance}]}
        if uri.endswith('/project/info'):
            return {'projectRoot': self.root, 'unityVersion': '2022.3.62f3',
                    'platform': 'StandaloneWindows64'}
        if uri.endswith('/editor/state'):
            return copy.deepcopy(self.state)
        raise AssertionError('Unexpected resource')

    def select(self, instance):
        if instance != self.instance:
            raise AssertionError('Wrong routing')

    def probe(self):
        if self.after_read:
            self.after_read()
        return copy.deepcopy(self.probe_result)


class IdentityTests(unittest.TestCase):
    setUp = fixtures.ControllerQueueTests.setUp
    open_service = fixtures.ControllerQueueTests.open_service
    receive = fixtures.ControllerQueueTests.receive
    event = fixtures.ControllerQueueTests.event
    stop_event = fixtures.ControllerQueueTests.stop_event
    accept = fixtures.ControllerQueueTests.accept
    queue = fixtures.ControllerQueueTests.queue

    def prepare(self):
        self.assertIsNotNone(importlib.util.find_spec('farmqa_identity'),
                             'Read-only request identity checker is not implemented')
        from farmqa_identity import inspect_request
        self.inspect = inspect_request
        self.root = Path(self.temp.name)/'client'
        self.root.mkdir()
        for args in (['init'], ['config','user.name','Fixture'],
                     ['config','user.email','fixture@example.invalid']):
            self.git(*args)
        (self.root/'source.txt').write_text('first\n', encoding='utf-8')
        self.git('add','source.txt'); self.git('commit','-m','fixture')
        self.target.update(repository=str(self.root), commit_sha=self.git('rev-parse','HEAD'))
        self.request_id = self.queue()
        self.editor = EditorFixture(self.root)

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def check(self):
        return self.inspect(self.db, self.request_id, 'Farm-Client@fixture',
                            'StandaloneWindows64', self.editor)

    def test_checkout_match_does_not_prove_loaded_build_or_server(self):
        self.prepare()
        result = self.check()
        self.assertEqual(result['checks']['source_commit'], 'match')
        self.assertEqual(result['checks']['loaded_source'], 'unknown')
        self.assertEqual(result['checks']['server_environment'], 'unknown')
        self.assertEqual(result['verdict'], 'BLOCKED')
        self.assertFalse(result['execution_enabled'])
        self.assertEqual(self.service.controller.status()[0]['state'], 'queued')

    def test_records_target_snapshot_and_allowlisted_evidence_per_inspection(self):
        self.prepare()
        self.editor.probe_result['credentials'] = 'DO-NOT-PERSIST'
        self.editor.probe_result['assemblies'][0]['token'] = 'DO-NOT-PERSIST'
        first = self.check()
        with self.service.db:
            self.service.sessions.set_target('linear-session', {**self.target,'commit_sha':'b'*40})
        second = self.check()
        self.assertNotEqual(first['observation_id'], second['observation_id'])
        with closing(sqlite3.connect(self.db)) as db:
            rows = db.execute('SELECT result_json FROM controller_identity_observations').fetchall()
        self.assertEqual(len(rows), 2)
        self.assertNotIn('DO-NOT-PERSIST', str(rows))
        self.assertEqual(second['target']['commit_sha'], self.target['commit_sha'])

    def test_project_commit_and_platform_mismatches_are_reported(self):
        self.prepare()
        self.editor.probe_result['dataPath'] = str(self.root/'other'/'Assets')
        self.editor.probe_result['buildTarget'] = 'Android'
        (self.root/'source.txt').write_text('second', encoding='utf-8')
        self.git('commit','-am','second')
        result = self.check()
        for key in ('project', 'source_commit', 'build_target'):
            self.assertEqual(result['checks'][key], 'mismatch', key)

    def test_dirty_file_hashes_and_changes_during_inspection(self):
        self.prepare()
        path = self.root/'source.txt'
        path.write_text('dirty', encoding='utf-8')
        self.editor.after_read = lambda: path.write_text('changed', encoding='utf-8')
        result = self.check()
        self.assertEqual(result['checks']['source_clean'], 'mismatch')
        self.assertEqual(result['checks']['source_stable'], 'mismatch')
        self.assertNotEqual(result['source_before']['dirty'][0]['sha256'],
                            result['source_after']['dirty'][0]['sha256'])

    def test_index_change_with_same_working_file_is_not_stable(self):
        self.prepare()
        path = self.root/'source.txt'
        path.write_text('index-one', encoding='utf-8'); self.git('add','source.txt')
        path.write_text('working', encoding='utf-8')
        def change_index():
            path.write_text('index-two', encoding='utf-8'); self.git('add','source.txt')
            path.write_text('working', encoding='utf-8')
        self.editor.after_read = change_index
        self.assertEqual(self.check()['checks']['source_stable'], 'mismatch')

    def test_stale_wrong_instance_and_playing_states_skip_probe(self):
        self.prepare()
        def forbidden():
            self.fail('Unsafe/stale state must not run the probe')
        self.editor.after_read = forbidden
        for change in ('stale','future','missing','instance','playing'):
            state = copy.deepcopy(self.editor.state)
            if change == 'stale': self.editor.state['observed_at_unix_ms'] -= 60000
            if change == 'future': self.editor.state['observed_at_unix_ms'] += 60000
            if change == 'missing': del self.editor.state['tests']
            if change == 'instance': self.editor.state['unity']['instance_id'] = 'other'
            if change == 'playing': self.editor.state['editor']['play_mode']['is_playing'] = True
            with self.subTest(change=change):
                result = self.check()
                self.assertEqual(result['checks']['editor_ready'], 'unknown')
                self.assertEqual(result['verdict'], 'BLOCKED')
            self.editor.state = state

    def test_missing_assemblies_and_editor_change_cannot_pass(self):
        self.prepare()
        self.editor.probe_result['assemblies'] = []
        self.editor.after_read = lambda: self.editor.state['compilation'].update(is_compiling=True)
        result = self.check()
        self.assertEqual(result['checks']['loaded_assemblies'], 'unknown')
        self.assertEqual(result['checks']['editor_ready'], 'unknown')

    def test_transport_failure_persists_blocked_without_raw_error(self):
        self.prepare()
        def broken(uri): raise OSError('secret error value')
        self.editor.read = broken
        result = self.check()
        self.assertEqual(result['verdict'], 'BLOCKED')
        self.assertEqual(result['error_type'], 'OSError')
        self.assertNotIn('secret error value', json.dumps(result))

    def test_malformed_final_timestamp_cannot_persist_untrusted_payload(self):
        self.prepare()
        for value in ({'credentials':'DO-NOT-PERSIST'}, 'DO-NOT-PERSIST', float('nan'), True):
            self.editor.state['observed_at_unix_ms'] = time.time()*1000
            self.editor.after_read = lambda: self.editor.state.update(observed_at_unix_ms=value)
            with self.subTest(value=value):
                result = self.check()
                self.assertIsNone(result['editor']['observed_after_ms'])
                self.assertEqual(result['checks']['editor_ready'], 'unknown')
        with closing(sqlite3.connect(self.db)) as db:
            saved = db.execute('SELECT result_json FROM controller_identity_observations').fetchall()
        self.assertNotIn('DO-NOT-PERSIST', str(saved))
        self.assertNotIn('NaN', str(saved))

    def test_unknown_or_inactive_request_does_not_inspect(self):
        self.prepare()
        def forbidden(uri): self.fail('Invalid request reached Unity')
        self.editor.read = forbidden
        self.request_id = 'unknown'
        with self.assertRaises(ValueError): self.check()
        self.request_id = self.service.controller.status()[0]['request_id']
        with self.service.db:
            self.service.controller.stop('org','linear-session',9999999999999)
        with self.assertRaises(ValueError): self.check()

    def test_stop_during_read_is_recorded_and_never_releases_reservation(self):
        self.prepare()
        def stop():
            with self.service.db:
                self.service.controller.stop('org','linear-session',9999999999999)
        self.editor.after_read = stop
        result = self.check()
        self.assertEqual(result['checks']['request_current'], 'mismatch')
        self.assertEqual(self.service.controller.status()[0]['state'], 'cancelled')


if __name__ == '__main__':
    unittest.main()
