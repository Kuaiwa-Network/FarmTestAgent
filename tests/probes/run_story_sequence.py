"""Supervised six-step Scripted story 10 replay. Stops at guide dialogue.

Uses a NEW synthetic ledger; outgoing Linear delivery is mocked. No login, guide click, skip, reward, breeding or arbitrary target is admitted.
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
from farmqa_authenticated_fixture import SESSION_FIELDS
from farmqa_story_sequence import StorySequenceAdapter, StorySequenceClient, sequence_binding, STEPS
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
    binding=sequence_binding(json.loads(args.binding.read_text(encoding='utf-8')))
    if args.output.resolve().is_relative_to(Path(binding['project']).resolve()):
        raise ValueError('Do not write evidence into client checkout')
    args.output.mkdir(parents=True,exist_ok=False)
    trace=[]
    def record(label,value):
        trace.append({'label':label,'observed_at_ms':int(time.time()*1000),'value':value})
        (args.output/'trace.json').write_text(json.dumps(trace,indent=2),encoding='utf-8')
        print(label,flush=True)
        return value
    client=StorySequenceClient();client.validate(binding)
    if binding['story_step']!=10:raise ValueError('Fresh observed story step 10 required')
    before=source_snapshot(binding['project'])
    sample=client.session_probe()
    assert evaluate(sample,binding)['session_match']=='match' and sample['generation_before']==binding['generation']
    send=Mock(return_value={'success':True,'agentActivity':{'id':'synthetic-reply'}})
    service=BridgeService(args.output/'synthetic.sqlite3','fixture-secret','fixture-client','fixture-app',
                          'fixture-org',send,bridge=Mock(thread_id='story-task'))
    store=service.controller;adapter=StorySequenceAdapter(store,client)
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
            request=store.enqueue('fixture-org:prompted:'+name);owner=store.acquire('supervised-story-sequence')
        assert owner['request_id']==request
        RequestSessionInspector(store).bind(request,owner['token'],{k:binding[k] for k in SESSION_FIELDS})
        return owner
    def observe(owner,predicate):
        end=time.monotonic()+15
        while True:
            value=adapter.observe(owner['request_id'],owner['token'])
            if predicate(value):return value
            if time.monotonic()>end:raise TimeoutError('Observation budget exhausted; retain owner')
            time.sleep(.15)
    try:
        deadline=time.monotonic()+15*60
        for step in STEPS:
            if time.monotonic()>deadline:raise TimeoutError('Sequence budget exhausted')
            owner=acquire('step-'+str(step))
            bound={**binding,'story_step':step,'run_id':uuid.uuid4().hex}
            began=time.monotonic()
            record('start_'+str(step),adapter.start(owner['request_id'],owner['token'],bound))
            # No start retry or recovery click. An uncertain response retains ownership.
            expected='finished' if step==60 else 'advanced'
            observed=record('observed_'+str(step),observe(owner,lambda v:v['completed'] and v['quiescent'] and v['outcome']==expected))
            assert observed['events']==['down','up','click'] and observed['success'] is True
            assert not observed['guard_lost']
            closed=adapter.finish(owner['request_id'],owner['token'])
            assert closed['outcome']==expected and closed['closed'] and closed['quiescent']
            record('transition_'+str(step),{'starting_story_step':step,
                'target':'endBtn' if step==60 else 'bgLoader at fresh continueHint centre',
                'command':'GameTestDriver.Click("endBtn",50)' if step==60 else 'GameTestDriver.ClickAt(fresh_x,fresh_y,50)',
                'expected_story_step':None if step==60 else step+10,
                'expected_outcome':expected,'elapsed_seconds':round(time.monotonic()-began,3),'result':closed})
            if closed['new_console_errors']:
                raise RuntimeError('Console errors observed; action safely closed, inspect evidence before continuing')
        assert source_snapshot(binding['project'])==before
        final_session=client.session_probe()
        assert evaluate(final_session,binding)['session_match']=='match' and final_session['generation_before']==binding['generation']
        record('final',{'source_unchanged':True,'session_still_matches':True,'states':[x['state'] for x in store.status()]})
    finally:service.close()


if __name__=='__main__':main()
