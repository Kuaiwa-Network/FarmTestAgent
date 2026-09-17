"""Opt-in live adapter verification on an already prepared/inspected QA panel.

No Play Mode switching, production DB access, real Linear traffic or game targets.
Faults are injected in the local transport wrapper, not by disrupting networking.
Any unexpected failure leaves the synthetic reservation held for investigation.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from farmqa_fixture_adapter import FixtureAdapter, FixtureClient, checked_binding
from farmqa_identity import source_snapshot
from linear_farmqa import BridgeService


def main():
    if not __debug__: raise RuntimeError('Assertions must be enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    binding = checked_binding(json.loads(args.binding.read_text(encoding='utf-8')))
    if args.output.resolve().is_relative_to(Path(binding['project']).resolve()):
        raise ValueError('Do not write evidence into the client checkout')
    args.output.mkdir(parents=True, exist_ok=False)
    trace = []
    def record(label, value):
        trace.append({'label':label,'observed_at_ms':int(time.time()*1000),'value':value})
        (args.output/'trace.json').write_text(json.dumps(trace,indent=2),encoding='utf-8')
        print(label,flush=True)
        return value

    class FaultClient(FixtureClient):
        before = None
        after = None
        def exchange(self, op, action_id, target):
            if self.before == op:
                self.before = None
                record('injected_before_'+op, {'action_id':action_id})
                raise TimeoutError('Injected before dispatch')
            result = super().exchange(op, action_id, target)
            record('remote_'+op,result)
            if self.after == op:
                self.after = None
                record('injected_after_'+op, {'action_id':action_id})
                raise TimeoutError('Injected after response received, before adapter receives it')
            return result

    client = FaultClient(); client.validate(binding)
    before = record('source_before',source_snapshot(binding['project']))
    record('editor',client.probe())
    session = record('session',client.session_probe())
    assert session.get('authenticated') is False and session.get('transport_connected') is False

    def rejected(label, operation, exception=ValueError):
        try: operation()
        except exception: record(label,{'rejected':True}); return
        raise AssertionError(label+' unexpectedly succeeded')

    rejected('wrong_module_rejected',lambda: client.exchange('start',uuid.uuid4().hex,
             {**binding,'hot_mvid':'00000000-0000-0000-0000-000000000000'}))
    bridge = Mock(thread_id='fixture-task')
    send = Mock(return_value={'success':True,'agentActivity':{'id':'fixture-reply'}})
    service = BridgeService(args.output/'synthetic.sqlite3','fixture-secret','fixture-client','fixture-app','fixture-org',send,bridge=bridge)
    store = service.controller
    adapter = FixtureAdapter(store,client)
    source_time = datetime.now(timezone.utc)-timedelta(seconds=1)
    target = {'repository':binding['project'],'requested_ref':'HEAD','commit_sha':binding['commit_sha'],
              'server_environment':'offline-login-fixture','selected_at':int(time.time()*1000),
              'source':'local_operator','verification':'not_verified_in_unity'}

    def receive(session_id, stop=False):
        event = {'type':'AgentSessionEvent','action':'prompted','webhookTimestamp':int(time.time()*1000),
                 'oauthClientId':'fixture-client','appUserId':'fixture-app','organizationId':'fixture-org',
                 'agentSession':{'id':session_id},'agentActivity':{'id':session_id+('-stop' if stop else ''),
                 'createdAt':(datetime.now(timezone.utc) if stop else source_time).isoformat(),
                 'content':{'type':'prompt','body':'synthetic fixture'}}}
        if stop: event['agentActivity']['signal']='stop'
        raw = json.dumps(event).encode()
        response = service.receive(raw,hmac.new(b'fixture-secret',raw,hashlib.sha256).hexdigest())
        assert response[0] == 200
        record('signed_stop' if stop else 'synthetic_prompt',{'session':session_id,'status':response[0]})

    for name in ('A','B','C'):
        with service.db:
            service.sessions.ensure(name,'fixture-task-'+name)
            service.sessions.set_target(name,target)
        receive(name)
        with service.db: store.enqueue('fixture-org:prompted:'+name)

    def acquire(name):
        with service.db: owner=store.acquire('fixture-adapter')
        assert owner['session_id']==name
        record('queue_acquired_'+name,store.status())
        return owner

    def observe_until(owner, predicate):
        end=time.monotonic()+15
        while time.monotonic()<end:
            value=adapter.observe(owner['request_id'],owner['token'])
            if predicate(value): return value
            time.sleep(.2)
        raise TimeoutError('Observation budget exhausted; retain reservation')

    a=acquire('A'); client.after='start'
    rejected('start_reply_lost',lambda:adapter.start(a['request_id'],a['token'],binding),TimeoutError)
    action_a=service.db.execute('SELECT action_id FROM controller_actions WHERE request_id=?',(a['request_id'],)).fetchone()[0]
    rejected('start_retry_rejected',lambda:adapter.start(a['request_id'],a['token'],binding))
    with service.db:
        rejected('early_release_rejected',lambda:store.release(a['request_id'],a['token']))
    competitor=subprocess.run([sys.executable,str(ROOT/'tools/farmqa_worker.py'),'--db',str(args.output/'synthetic.sqlite3'),'--seconds','0'],capture_output=True,text=True,timeout=10)
    assert competitor.returncode==0 and json.loads(competitor.stdout)['outcome']=='blocked'
    record('competing_process',json.loads(competitor.stdout))
    observe_until(a,lambda x:x['events']==['down'])
    receive('A',stop=True); client.before='cancel'
    rejected('cancel_not_delivered',lambda:adapter.observe(a['request_id'],a['token']),TimeoutError)
    stopped=observe_until(a,lambda x:x['completed'] and x['quiescent'])
    assert stopped['cancel_requested'] and stopped['success'] is False and stopped['events']==['down','up']
    client.after='close'
    rejected('close_reply_lost',lambda:adapter.finish(a['request_id'],a['token']),TimeoutError)
    with service.db: assert store.acquire('competitor') is None
    assert record('finished_A',adapter.finish(a['request_id'],a['token']))['reservation_state']=='cancelled'

    b=acquire('B'); adapter.start(b['request_id'],b['token'],binding)
    observe_until(b,lambda x:x['events']==['down'])
    rejected('retired_owner_rejected',lambda:adapter.observe(a['request_id'],a['token']))
    # Deliberately deliver old protocol packets below the Python gate. Remote
    # tombstones must make them harmless to B; never spoof B's action identity.
    assert client.exchange('start',action_a,binding)['closed'] is True
    assert client.exchange('cancel',action_a,binding)['closed'] is True
    live_b=adapter.observe(b['request_id'],b['token'])
    assert not live_b['cancel_requested'] and live_b['events']==['down']
    completed_b=observe_until(b,lambda x:x['completed'] and x['quiescent'])
    assert completed_b['success'] is True and completed_b['events']==['down','up','click']
    assert record('finished_B',adapter.finish(b['request_id'],b['token']))['reservation_state']=='released'

    c=acquire('C'); client.before='start'
    rejected('start_not_delivered',lambda:adapter.start(c['request_id'],c['token'],binding),TimeoutError)
    action_c=service.db.execute('SELECT action_id FROM controller_actions WHERE request_id=?',(c['request_id'],)).fetchone()[0]
    receive('C',stop=True)
    fenced=adapter.observe(c['request_id'],c['token'])
    assert not fenced['started'] and fenced['cancel_requested'] and fenced['completed']
    assert record('finished_C',adapter.finish(c['request_id'],c['token']))['reservation_state']=='cancelled'
    late=client.exchange('start',action_c,binding)
    assert late['closed'] and not late['started'] and late['events']==[]
    record('queue_final',store.status())
    cleanup_code=(ROOT/'tests/probes/pointer-cancellation.cs.txt').read_text(encoding='utf-8').replace('__OP__','cleanup').replace('__RUN_ID__',binding['run_id'])
    cleanup=client._payload(client._rpc('tools/call',{'name':'execute_code','arguments':{
        'action':'execute','code':cleanup_code,'safety_checks':True}}),'content')['result']
    record('cleanup',cleanup)
    assert not cleanup['fixture_present'] and cleanup['quiescent']
    assert cleanup['events']==['down','up','down','up','click']
    assert all(row['value']['new_console_errors']==0 for row in trace if row['label'].startswith('remote_'))
    assert before==record('source_after',source_snapshot(binding['project']))
    bridge.dispatch.assert_not_called()
    service.close()
    record('result',{'status':'PASS','scope':'fixture adapter with locally injected transport faults','gameplay_actions':0,'production_deployed':False})


if __name__=='__main__': main()
