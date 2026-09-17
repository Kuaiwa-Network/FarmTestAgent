"""Supervised authenticated counter-panel replay. No login or game controls.

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
from farmqa_authenticated_fixture import AuthenticatedFixtureAdapter, AuthenticatedFixtureClient, authenticated_binding, SESSION_FIELDS
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

    class Client(AuthenticatedFixtureClient):
        lose_start=False
        drop_start=False
        last_error=None
        def _rpc(self,method,params,notification=False):
            value=super()._rpc(method,params,notification)
            if method=='tools/call' and params.get('name')=='execute_code':
                payload=json.loads(value['content'][0]['text'])
                self.last_error=payload.get('message') if payload.get('success') is False else None
            return value
        def exchange(self,op,action_id,target):
            if op=='start' and self.drop_start:
                self.drop_start=False
                raise TimeoutError('Injected BEFORE dispatch')
            value=super().exchange(op,action_id,target)
            if op=='start' and self.lose_start:
                self.lose_start=False
                record('lost_start_response',value)
                raise TimeoutError('Injected AFTER response')
            return value
    client=Client();client.validate(binding)
    before=source_snapshot(binding['project'])
    sample=client.session_probe()
    assert evaluate(sample,binding)['session_match']=='match' and sample['generation_before']==binding['generation']
    record('setup',client.panel('setup',binding))

    def close_raw(action,target):
        end=time.monotonic()+15
        while True:
            value=client.exchange('status',action,target)
            if value['completed'] and value['quiescent']: break
            if time.monotonic()>end: raise TimeoutError('Fixture action not quiescent')
            time.sleep(.15)
        return client.exchange('close',action,target)

    # Intentionally below Python's immutable binding gate to exercise Unity admission.
    for field,value in [('player_id',binding['player_id']%4294967295+1),
                        ('route_sha256','0'*64 if binding['route_sha256']!='0'*64 else '1'*64),
                        ('generation',binding['generation']%4294967295+1)]:
        action=uuid.uuid4().hex;wrong={**binding,field:value}
        result=record('reject_'+field,client.exchange('start',action,wrong))
        assert result['admission']=='session_rejected' and not result['started'] and result['events']==[]
        assert result['completed'] and result['quiescent'] and result['cancel_requested']
        closed=close_raw(action,wrong);assert closed['events']==[] and closed['closed']

    send=Mock(return_value={'success':True,'agentActivity':{'id':'synthetic-reply'}})
    service=BridgeService(args.output/'synthetic.sqlite3','fixture-secret','fixture-client','fixture-app',
                          'fixture-org',send,bridge=Mock(thread_id='fixture-task'))
    store=service.controller;adapter=AuthenticatedFixtureAdapter(store,client)
    target={'repository':binding['project'],'commit_sha':binding['commit_sha'],'requested_ref':'HEAD',
            'server_environment':binding['server_environment'],'selected_at':time.time(),
            'source':'local_operator','verification':'not_verified_in_unity'}
    def receive(name,stop=False):
        stamp=datetime.now(timezone.utc)-timedelta(seconds=0 if stop else 1)
        event={'type':'AgentSessionEvent','action':'prompted','webhookTimestamp':int(time.time()*1000),
               'oauthClientId':'fixture-client','appUserId':'fixture-app','organizationId':'fixture-org',
               'agentSession':{'id':name},'agentActivity':{'id':name+('-stop' if stop else ''),
               'createdAt':stamp.isoformat(),'content':{'type':'prompt','body':'synthetic fixture'}}}
        if stop:event['agentActivity']['signal']='stop'
        raw=json.dumps(event).encode()
        assert service.receive(raw,hmac.new(b'fixture-secret',raw,hashlib.sha256).hexdigest())[0]==200
    def acquire(name):
        with service.db:
            service.sessions.ensure(name,'fixture-task-'+name);service.sessions.set_target(name,target)
        receive(name)
        with service.db:
            request=store.enqueue('fixture-org:prompted:'+name);owner=store.acquire('authenticated-fixture')
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
    def fixture_fault(restore=False):
        code='''var f=System.AppDomain.CurrentDomain.GetData("FarmQA.AuthenticatedFixture") as System.Collections.Generic.Dictionary<string,object>;
if(f==null || (string)f["run_id"]!="RUN") throw new System.Exception("Wrong QA fixture");
BODY
return new { fixture_only_fault=true };'''.replace('RUN',binding['run_id'])
        body=('f["session_check"]=f["saved_session_check"]; f.Remove("saved_session_check");' if restore else
              'if(f.ContainsKey("saved_session_check")) throw new System.Exception("Fault already set"); f["saved_session_check"]=f["session_check"]; f["session_check"]=(System.Func<bool>)(()=>false);')
        return client._payload(client._rpc('tools/call',{'name':'execute_code','arguments':{
            'action':'execute','code':code.replace('BODY',body),'safety_checks':True}}),'content')['result']
    try:
        a=acquire('A');client.lose_start=True
        rejected('lost_reply_held',lambda:adapter.start(a['request_id'],a['token'],binding),TimeoutError)
        rejected('start_never_retried',lambda:adapter.start(a['request_id'],a['token'],binding))
        record('A_held',observe(a,lambda v:v['events']==['down'] and not v['completed']))
        receive('A',True)
        final=record('A_cancelled',finish(a))
        assert final['admission']=='accepted' and final['events']==['down','up'] and final['success'] is False
        assert final['reservation_state']=='cancelled'

        b=acquire('B');adapter.start(b['request_id'],b['token'],binding)
        record('B_held',observe(b,lambda v:v['events']==['down'] and not v['completed']))
        for op in ('start','cancel'):
            old=record('A_late_'+op,client.exchange(op,id_for(a),binding));assert old['closed']
        final=record('B_completed',finish(b))
        assert final['events']==['down','up','click'] and final['success'] is True and not final['session_lost']

        c=acquire('C');adapter.start(c['request_id'],c['token'],binding)
        record('C_held',observe(c,lambda v:v['events']==['down'] and not v['completed']))
        record('injected_fixture_session_loss',fixture_fault())
        final=record('C_session_cancelled',finish(c))
        assert final['session_lost'] and final['cancel_requested'] and final['events']==['down','up'] and final['success'] is False
        record('restored_fixture_session_check',fixture_fault(True))

        d=acquire('D');client.drop_start=True
        rejected('start_not_dispatched',lambda:adapter.start(d['request_id'],d['token'],binding),TimeoutError)
        receive('D',True);final=record('D_cancel_before_start',finish(d))
        assert final['admission']=='cancelled_before_start' and not final['started'] and final['events']==[]
        late=record('D_late_start',client.exchange('start',id_for(d),binding));assert late['closed'] and not late['started']
        record('cleanup_first_run',client.panel('cleanup',binding))
        rejected('same_run_setup_rejected',lambda:client.panel('setup',binding))
        assert client.last_error=='Runtime error: Fixture run already used or capacity exhausted'

        newer={**binding,'run_id':uuid.uuid4().hex}
        record('setup_new_run',client.panel('setup',newer));action=uuid.uuid4().hex
        record('new_run_start',client.exchange('start',action,newer))
        for op in ('start','cancel'):
            rejected('old_run_'+op+'_rejected',lambda op=op:client.exchange(op,id_for(d),binding))
            assert client.last_error=='Runtime error: Fixture identity lost or mismatched'
        final=record('new_run_completed',close_raw(action,newer))
        assert final['events']==['down','up','click'] and final['success'] is True and not final['session_lost']
        record('cleanup_new_run',client.panel('cleanup',newer))
        assert source_snapshot(binding['project'])==before
        assert evaluate(client.session_probe(),binding)['session_match']=='match'
        record('final',{'source_unchanged':True,'session_still_matches':True,
                        'states':[x['state'] for x in store.status()]})
    finally:
        service.close()


if __name__=='__main__':main()
