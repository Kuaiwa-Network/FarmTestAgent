"""Owner-bound, read-only session evidence. Never an action permit or session lease."""
import json
from pathlib import Path
import re
import time
import uuid

from farmqa_controller import checked_target
from farmqa_identity import project_matches, safe_text, source_snapshot
from farmqa_session_identity import evaluate
from farmqa_unity_identity import UnityIdentityClient


def checked_expectation(raw):
    fields = {'instance', 'build_target', 'hot_mvid', 'server_environment', 'player_id', 'route_sha256'}
    if not isinstance(raw, dict) or set(raw) != fields:
        raise ValueError('Exact private session expectation required')
    if (not safe_text(raw['instance'], 256) or not safe_text(raw['server_environment'], 128)
            or raw['build_target'] != 'StandaloneWindows64'
            or type(raw['player_id']) is not int or not 0 < raw['player_id'] <= 4294967295
            or not isinstance(raw['route_sha256'], str)
            or not re.fullmatch('[a-f0-9]{64}', raw['route_sha256'])
            or not isinstance(raw['hot_mvid'], str)
            or not re.fullmatch('[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}', raw['hot_mvid'])):
        raise ValueError('Unsupported private session expectation')
    return dict(raw)


class RequestSessionInspector:
    """Explicit local library; no CLI tokens, dispatch, login, release or retries.

    Bind once while owning the request. Remote reads run without a SQLite lock.
    Recheck the owner and target under a write lock before appending evidence.
    Bindings/observations belong in the private controller ledger, never Git.
    """
    def __init__(self, store, client=None):
        self.store, self.db = store, store.db
        self.client = client or UnityIdentityClient()

    def _entry(self):
        if self.db.in_transaction:
            raise ValueError('Do not hold a transaction across session inspection')

    def _active(self, request_id, token):
        row = self.store._owned(request_id, token)
        if row['state'] != 'active': raise ValueError('An active owned request is required')
        return row

    def bind(self, request_id, token, expected):
        """Pin independent operator expectations; never learn them from a sample."""
        self._entry()
        expected = checked_expectation(expected)
        with self.db:
            self.store._write_lock()
            row = self._active(request_id, token)
            target = checked_target(row['target_json'])
            if target['server_environment'] != expected['server_environment']:
                raise ValueError('Expected environment does not match the pinned request')
            self.db.execute('''CREATE TABLE IF NOT EXISTS controller_session_bindings (
                request_id TEXT PRIMARY KEY, target_json TEXT NOT NULL, expected_json TEXT NOT NULL)''')
            previous = self.db.execute('SELECT * FROM controller_session_bindings WHERE request_id=?',
                                       (request_id,)).fetchone()
            if previous:
                if (previous['target_json'] != row['target_json'] or
                        json.loads(previous['expected_json']) != expected):
                    raise ValueError('Session binding is immutable; use a new request')
            else:
                self.db.execute('INSERT INTO controller_session_bindings VALUES (?,?,?)',
                                (request_id, row['target_json'], json.dumps(expected, sort_keys=True)))

    def _editor(self, target, expected):
        client = self.client
        instances = client.read('mcpforunity://instances')['instances']
        if len(instances) != 1 or instances[0]['id'] != expected['instance']:
            raise ValueError('Expected one exact Editor')
        client.select(expected['instance'])
        info = client.read('mcpforunity://project/info')
        if not project_matches(info.get('projectRoot'), target['repository']):
            raise ValueError('Editor project mismatch')
        state = client.read('mcpforunity://editor/state')
        probe = client.probe()
        assemblies = probe.get('assemblies')
        hot = ([a.get('moduleMvid') for a in assemblies if isinstance(a, dict) and a.get('name') == 'HotUpdate']
               if isinstance(assemblies, list) else [])
        return (state.get('tests', {}).get('is_running') is False
                and info.get('platform') == probe.get('buildTarget') == expected['build_target']
                and project_matches(probe.get('dataPath'), Path(target['repository'])/'Assets')
                and hot == [expected['hot_mvid']]
                and probe.get('isPlaying') is True and probe.get('isPlayingOrWillChangePlaymode') is True
                and probe.get('isCompiling') is False and probe.get('isUpdating') is False)

    def inspect(self, request_id, token):
        self._entry()
        owner = self._active(request_id, token)
        if not self.db.execute("SELECT 1 FROM sqlite_master WHERE name='controller_session_bindings'").fetchone():
            raise ValueError('No pinned session expectation')
        binding = self.db.execute('SELECT * FROM controller_session_bindings WHERE request_id=?', (request_id,)).fetchone()
        if not binding or binding['target_json'] != owner['target_json']:
            raise ValueError('Missing or changed request binding')
        expected = checked_expectation(json.loads(binding['expected_json']))
        target = checked_target(binding['target_json'])
        result = {'schema_version':1, 'observation_id':uuid.uuid4().hex, 'request_id':request_id,
                  'mode':'read_only_request_session', 'started_at':time.time(),
                  'checks':{'source':'unknown', 'editor':'unknown', 'session':'unknown', 'request_current':'unknown'},
                  'request_session_match':'unknown', 'verdict':'BLOCKED', 'execution_enabled':False}
        sample = None
        try:
            before = source_snapshot(target['repository'])
            self.client.read('mcpforunity://custom-tools')
            editor_before = self._editor(target, expected)
            sample = self.client.session_probe()
            editor_after = self._editor(target, expected)
            after = source_snapshot(target['repository'])
            result['checks']['source'] = 'match' if (before == after and not before['dirty']
                and before['commit_sha'] == target['commit_sha']) else 'mismatch'
            result['checks']['editor'] = 'match' if editor_before and editor_after else 'mismatch'
        except Exception as exc:
            sample = None
            result['error_type'] = type(exc).__name__
        # No external calls under this lock. A Stop can be recorded during reads.
        with self.db:
            self.store._write_lock()
            try:
                current = self._active(request_id, token)
                pinned = self.db.execute('SELECT * FROM controller_session_bindings WHERE request_id=?', (request_id,)).fetchone()
                current_matches = (current['target_json'] == owner['target_json']
                                   and current['owner'] == owner['owner']
                                   and current['acquired_at'] == owner['acquired_at']
                                   and pinned is not None and tuple(pinned) == tuple(binding))
            except ValueError:
                current_matches = False
            result['checks']['request_current'] = 'match' if current_matches else 'mismatch'
            # Evaluate freshness after all remote work AND after acquiring the lock.
            result['checks']['session'] = evaluate(sample, expected)['session_match']
            status = sample.get('status') if isinstance(sample, dict) else None
            if status in ('observed','edit_mode','busy','missing_objects','unsupported_schema','unavailable'):
                result['observation_status'] = status
            if all(value == 'match' for value in result['checks'].values()):
                result['request_session_match'] = 'match'
            result['finished_at'] = time.time()
            self.db.execute('''CREATE TABLE IF NOT EXISTS controller_session_observations (
                observation_id TEXT PRIMARY KEY, request_id TEXT NOT NULL, result_json TEXT NOT NULL)''')
            self.db.execute('INSERT INTO controller_session_observations VALUES (?,?,?)',
                            (result['observation_id'], request_id, json.dumps(result)))
        return result
