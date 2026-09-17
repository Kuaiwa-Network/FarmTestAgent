"""Opt-in authenticated counter fixture. No game controls or general action API."""
import base64
import json
from pathlib import Path
import re

from farmqa_fixture_adapter import FixtureAdapter, FixtureClient, checked_binding, checked_observation
from farmqa_identity import project_matches
from farmqa_request_session import checked_expectation

FIXTURE_FIELDS = {'instance','project','commit_sha','hot_mvid','build_target','run_id'}
SESSION_FIELDS = {'instance','hot_mvid','build_target','server_environment','player_id','route_sha256'}


def authenticated_binding(raw):
    if not isinstance(raw,dict) or set(raw) != FIXTURE_FIELDS | SESSION_FIELDS | {'generation'}:
        raise ValueError('Exact authenticated fixture binding required')
    checked_binding({k:raw[k] for k in FIXTURE_FIELDS})
    checked_expectation({k:raw[k] for k in SESSION_FIELDS})
    if type(raw['generation']) is not int or not 0 < raw['generation'] <= 4294967295:
        raise ValueError('Expected authenticated session generation required')
    return dict(raw)


def authenticated_observation(raw, action_id, binding):
    result = checked_observation(raw,action_id,binding)
    admission = raw.get('admission')
    if (admission not in ('accepted','session_rejected','cancelled_before_start')
            or type(raw.get('session_lost')) is not bool
            or (admission == 'accepted') != result['started']
            or admission != 'accepted' and not result['cancel_requested']):
        raise ValueError('Unknown or inconsistent session admission')
    return {**result,'admission':admission,'session_lost':raw['session_lost']}


class AuthenticatedFixtureClient(FixtureClient):
    def _call(self, op, action_id, binding):
        binding = authenticated_binding(binding)
        self.select(binding['instance'])
        probes = Path(__file__).resolve().parents[1]/'tests/probes'
        code = (probes/'authenticated-fixture.cs.txt').read_text(encoding='utf-8')
        code = code.replace('__SESSION_PROBE__',(probes/'session-identity.cs.txt').read_text(encoding='utf-8-sig'))
        for key,value in {'OP':op,'ACTION_ID':action_id,'RUN_ID':binding['run_id'],
                          'PROJECT_B64':base64.b64encode(binding['project'].encode()).decode(),
                          'MVID':binding['hot_mvid'],'BUILD':binding['build_target'],
                          'PLAYER':str(binding['player_id']),'GENERATION':str(binding['generation']),
                          'ROUTE':binding['route_sha256']}.items():
            code = code.replace('__'+key+'__',value)
        result = self._payload(self._rpc('tools/call',{'name':'execute_code','arguments':{
            'action':'execute','code':code,'safety_checks':True}}),'content')
        return result['result']

    def exchange(self, op, action_id, binding):
        if op not in ('start','status','cancel','close') or not re.fullmatch('[a-f0-9]{32}',action_id):
            raise ValueError('Unsupported authenticated fixture operation')
        return self._call(op,action_id,binding)

    def panel(self, op, binding):
        if op not in ('setup','cleanup'): raise ValueError('Unsupported panel operation')
        self.validate(authenticated_binding(binding))
        return self._call(op,'0'*32,binding)


class AuthenticatedFixtureAdapter(FixtureAdapter):
    _binding = staticmethod(authenticated_binding)
    _observation = staticmethod(authenticated_observation)

    def _target(self, row, binding):
        target = json.loads(row['target_json'])
        if (not project_matches(binding['project'],target['repository'])
                or target['commit_sha'] != binding['commit_sha']
                or target['server_environment'] != binding['server_environment']):
            raise ValueError('Authenticated fixture target mismatch')
        if not self.db.execute("SELECT 1 FROM sqlite_master WHERE name='controller_session_bindings'").fetchone():
            raise ValueError('Independent request/session binding required')
        pinned = self.db.execute('SELECT * FROM controller_session_bindings WHERE request_id=?', (row['request_id'],)).fetchone()
        if (not pinned or pinned['target_json'] != row['target_json']
                or json.loads(pinned['expected_json']) != {k:binding[k] for k in SESSION_FIELDS}):
            raise ValueError('Request/session expectation mismatch')
