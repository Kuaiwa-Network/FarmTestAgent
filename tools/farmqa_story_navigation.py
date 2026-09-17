"""Opt-in scripted story 10, step 10 -> 20 only. No general game action API."""
import base64
from pathlib import Path
import re

from farmqa_authenticated_fixture import AuthenticatedFixtureAdapter, authenticated_binding
from farmqa_fixture_adapter import FixtureClient, checked_observation


def story_observation(raw, action_id, binding, *, expected_step=10, expected_next=20):
    result=checked_observation(raw,action_id,binding)
    admission=raw.get('admission')
    step=raw.get('story_step')
    outcome=raw.get('outcome')
    if (admission not in ('accepted','session_rejected','state_rejected','cancelled_before_start')
        or (admission=='accepted') != result['started']
        or admission!='accepted' and not result['cancel_requested']
        or 'story_step' not in raw
        or type(raw.get('guard_lost')) is not bool
        or not result['started'] and (result['success'] is not None or result['events']!=[])
        or step is not None and (type(step) is not int or not 0<step<=4294967295)
        or outcome not in ('advanced','unchanged','unexpected','unavailable')
        or outcome=='advanced' and (admission!='accepted' or not result['started'] or result['events']!=['down','up','click'] or step!=expected_next or result['success'] is not True or not result['completed'] or raw['guard_lost'])
        or outcome=='unchanged' and step!=expected_step
        or outcome=='unavailable' and step is not None):
        raise ValueError('Unknown or inconsistent story outcome')
    return {**result,'admission':admission,'guard_lost':raw['guard_lost'],
            'story_step':step,'outcome':outcome}


class StoryNavigationClient(FixtureClient):
    _binding=staticmethod(authenticated_binding)

    def _story_parameters(self, binding):
        return {'STORY_STEP':'10','STORY_NEXT':'20','SEQUENCE':'false'}

    def exchange(self, op, action_id, binding):
        binding=self._binding(binding)
        if op not in ('start','status','cancel','close') or not re.fullmatch('[a-f0-9]{32}',action_id):
            raise ValueError('Unsupported story operation')
        self.select(binding['instance'])
        probes=Path(__file__).resolve().parents[1]/'tests/probes'
        code=(probes/'story-navigation.cs.txt').read_text(encoding='utf-8')
        code=code.replace('__SESSION_PROBE__',(probes/'session-identity.cs.txt').read_text(encoding='utf-8-sig'))
        for key,value in {'OP':op,'ACTION_ID':action_id,'RUN_ID':binding['run_id'],
            'PROJECT_B64':base64.b64encode(binding['project'].encode()).decode(),
            'MVID':binding['hot_mvid'],'BUILD':binding['build_target'],
            'PLAYER':str(binding['player_id']),'GENERATION':str(binding['generation']),
            'ROUTE':binding['route_sha256'],**self._story_parameters(binding)}.items():code=code.replace('__'+key+'__',value)
        return self._payload(self._rpc('tools/call',{'name':'execute_code','arguments':{
            'action':'execute','code':code,'safety_checks':True}}),'content')['result']


class StoryNavigationAdapter(AuthenticatedFixtureAdapter):
    _observation=staticmethod(story_observation)
