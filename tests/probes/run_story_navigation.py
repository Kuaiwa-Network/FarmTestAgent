"""Supervised single story step 10 -> 20 replay. No login, skip or finish.

Uses a NEW synthetic ledger; outgoing Linear delivery is mocked. Faults are
injected locally and in QA fixture state, never by changing the game session.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
import sys
import time
import uuid
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from farmqa_authenticated_fixture import authenticated_binding, SESSION_FIELDS
from farmqa_story_navigation import StoryNavigationAdapter, StoryNavigationClient
from farmqa_identity import source_snapshot
from farmqa_request_session import RequestSessionInspector
from farmqa_session_identity import evaluate
from linear_farmqa import BridgeService


def main():
    if not __debug__: raise RuntimeError('Assertions must be enabled')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    binding=authenticated_binding(json.loads(args.binding.read_text(encoding='utf-8')))
    if args.output.resolve().is_relative_to(Path(binding['project']).resolve()):
        raise ValueError('Do not write evidence into client checkout')
    args.output.mkdir(parents=True,exist_ok=False)
    trace=[]
    def record(label,value):
        trace.append({'label':label,'observed_at_ms':int(time.time()*1000),'value':value})
        (args.output/'trace.json').write_text(json.dumps(trace,indent=2),encoding='utf-8')
        print(label,flush=True)
        return value
    class Client(StoryNavigationClient):
        lose_start=False
        drop_start=False
        capture_fault=False
        def _rpc(self,method,params,notification=False):
            if self.capture_fault and method=='tools/call' and params.get('name')=='execute_code':
                self.capture_fault=False
                code=params['arguments']['code']
                needle='record["task"]=task;'
                assert code.count(needle)==1
                # Fixture-only predicate fault after admission. Remove the update
                # monitor to prove the event-boundary guard itself blocks bubbling.
                code=code.replace(needle,needle+'record["ready"]=(System.Func<bool>)(()=>false); UnityEditor.EditorApplication.update-=(UnityEditor.EditorApplication.CallbackFunction)record["monitor"];')
                params={**params,'arguments':{**params['arguments'],'code':code}}
            return super()._rpc(method,params,notification)
        def exchange(self,op,action,target):
            if op=='start' and self.drop_start:
                self.drop_start=False;raise TimeoutError('Injected BEFORE dispatch')
            result=super().exchange(op,action,target)
            if op=='start' and self.lose_start:
                self.lose_start=False;record('lost_start_response',result)
                raise TimeoutError('Injected AFTER response')
            return result
    client=Client();client.validate(binding)
    before=source_snapshot(binding['project'])
    sample=client.session_probe()
    assert evaluate(sample,binding)['session_match']=='match' and sample['generation_before']==binding['generation']
    def close_raw(action,target):
        result=client.exchange('close',action,target)
        assert result['closed'] and result['quiescent']
        return result
    for field,value in [('player_id',binding['player_id']%4294967295+1),
                        ('route_sha256','0'*64 if binding['route_sha256']!='0'*64 else '1'*64),
                        ('generation',binding['generation']%4294967295+1)]:
        action=uuid.uuid4().hex;wrong={**binding,field:value,'run_id':uuid.uuid4().hex}
        result=record('reject_'+field,client.exchange('start',action,wrong))
        assert result['admission']=='session_rejected' and not result['started'] and result['events']==[]
        assert result['story_step']==10 and result['outcome']=='unchanged'
        close_raw(action,wrong)
    send=Mock(return_value={'success':True,'agentActivity':{'id':'synthetic-reply'}})
    service=BridgeService(args.output/'synthetic.sqlite3','fixture-secret','fixture-client','fixture-app',
                          'fixture-org',send,bridge=Mock(thread_id='story-task'))
    store=service.controller;adapter=StoryNavigationAdapter(store,client)
    target={'repository':binding['project'],'commit_sha':binding['commit_sha'],'requested_ref':'HEAD',
            'server_environment':binding['server_environment'],'selected_at':time.time(),
            'source':'local_operator','verification':'not_verified_in_unity'}
    def receive(name,stop=False):
        stamp=datetime.now(timezone.utc)-timedelta(seconds=0 if stop else 1)
        event={'type':'AgentSessionEvent','action':'prompted','webhookTimestamp':int(time.time()*1000),
               'oauthClientId':'fixture-client','appUserId':'fixture-app','organizationId':'fixture-org',
               'agentSession':{'id':name},'agentActivity':{'id':name+('-stop' if stop else ''),
               'createdAt':stamp.isoformat(),'content':{'type':'prompt','body':'synthetic story navigation'}}}
        if stop:event['agentActivity']['signal']='stop'
        raw=json.dumps(event).encode()
        assert service.receive(raw,hmac.new(b'fixture-secret',raw,hashlib.sha256).hexdigest())[0]==200
    def acquire(name):
        with service.db:
            service.sessions.ensure(name,'story-task-'+name);service.sessions.set_target(name,target)
        receive(name)
        with service.db:
            request=store.enqueue('fixture-org:prompted:'+name);owner=store.acquire('supervised-story-navigation')
        assert owner['request_id']==request
        RequestSessionInspector(store).bind(request,owner['token'],{k:binding[k] for k in SESSION_FIELDS})
        return owner
    def rejected(label,fn,exception=ValueError):
        try:fn()
        except exception:record(label,{'rejected':True});return
        raise AssertionError(label+' unexpectedly succeeded')
    def observe(owner,predicate):
        end=time.monotonic()+15
        while True:
            value=adapter.observe(owner['request_id'],owner['token'])
            if predicate(value):return value
            if time.monotonic()>end:raise TimeoutError('Observation budget exhausted; retain owner')
            time.sleep(.15)
    def finish(owner):
        observe(owner,lambda v:v['completed'] and v['quiescent'])
        return adapter.finish(owner['request_id'],owner['token'])
    def id_for(owner):
        return service.db.execute('SELECT action_id FROM controller_actions WHERE request_id=?',(owner['request_id'],)).fetchone()[0]
    bindings={}
    def begin(owner,**faults):
        target={**binding,'run_id':uuid.uuid4().hex};bindings[owner['request_id']]=target
        for name,value in faults.items():setattr(client,name,value)
        return adapter.start(owner['request_id'],owner['token'],target)
    try:
        a=acquire('A')
        rejected('start_not_dispatched',lambda:begin(a,drop_start=True),TimeoutError)
        receive('A',True);cancelled=record('cancel_before_start',finish(a))
        assert cancelled['admission']=='cancelled_before_start' and not cancelled['started'] and cancelled['events']==[]
        old_binding=bindings[a['request_id']]
        late=record('late_cancelled_start',client.exchange('start',id_for(a),old_binding))
        assert late['closed'] and not late['started'] and late['story_step']==10

        g=acquire('G');begin(g,capture_fault=True)
        guarded=record('capture_guard_rejection',finish(g))
        assert guarded['guard_lost'] and guarded['cancel_requested'] and guarded['success'] is False
        assert guarded['events']==[] and guarded['story_step']==10 and guarded['outcome']=='unchanged'

        b=acquire('B')
        rejected('lost_reply_held',lambda:begin(b,lose_start=True),TimeoutError)
        rejected('start_never_retried',lambda:adapter.start(b['request_id'],b['token'],bindings[b['request_id']]))
        completed=record('story_advanced',finish(b))
        assert completed['admission']=='accepted' and completed['events']==['down','up','click']
        assert completed['success'] is True and completed['outcome']=='advanced' and completed['story_step']==20
        assert completed['new_console_errors']==0 and not completed['guard_lost']
        for op in ('start','cancel'):
            old=record('old_A_'+op,client.exchange(op,id_for(a),old_binding))
            assert old['closed'] and not old['started']
        c=acquire('C');rejected_state=record('advanced_state_rejected',begin(c))
        assert rejected_state['admission']=='state_rejected' and not rejected_state['started']
        assert rejected_state['story_step']==20 and rejected_state['events']==[]
        record('C_closed',finish(c))
        assert source_snapshot(binding['project'])==before
        final_session=client.session_probe()
        assert evaluate(final_session,binding)['session_match']=='match' and final_session['generation_before']==binding['generation']
        record('final',{'source_unchanged':True,'session_still_matches':True,'states':[x['state'] for x in store.status()]})
    finally:service.close()


if __name__=='__main__':main()
