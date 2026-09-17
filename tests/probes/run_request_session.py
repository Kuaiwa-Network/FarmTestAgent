"""Opt-in diagnostic replay against an already inspected Unity session.

Creates a NEW private synthetic ledger, never consumes the production queue,
logs in, injects input, changes Play Mode or sends real Linear traffic.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
import sys
import time
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from farmqa_identity import source_snapshot
from farmqa_request_session import RequestSessionInspector, checked_expectation
from farmqa_unity_identity import UnityIdentityClient
from linear_farmqa import BridgeService


def check_case(result, expected_checks):
    """An unknown aggregate alone does not prove the intended negative case."""
    assert result['checks'] == expected_checks
    wanted = 'match' if all(v == 'match' for v in expected_checks.values()) else 'unknown'
    assert result['request_session_match'] == wanted
    assert result['verdict'] == 'BLOCKED' and result['execution_enabled'] is False


def main():
    if not __debug__: raise RuntimeError('Assertions must be enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--expected', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('authenticated','edit-mode'), required=True)
    args = parser.parse_args()
    expected = checked_expectation(json.loads(args.expected.read_text(encoding='utf-8')))
    if args.output.resolve().is_relative_to(args.project.resolve()):
        raise ValueError('Do not write evidence into the client checkout')
    before = source_snapshot(args.project)
    assert before['commit_sha'] == args.commit and not before['dirty']
    args.output.mkdir(parents=True, exist_ok=False)
    trace = []
    def record(label, result):
        trace.append({'label':label, 'result':result})
        (args.output/'trace.json').write_text(json.dumps(trace, indent=2), encoding='utf-8')
        print(label, flush=True)

    service = BridgeService(args.output/'synthetic.sqlite3', 'fixture-secret', 'fixture-client',
                            'fixture-app', 'fixture-org', Mock(), bridge=Mock(thread_id='fixture-task'))
    store = service.controller
    target = {'repository':str(args.project.resolve()), 'requested_ref':'HEAD', 'commit_sha':args.commit,
              'server_environment':expected['server_environment'], 'selected_at':time.time(),
              'source':'local_operator', 'verification':'not_verified_in_unity'}
    def receive(name, stop=False):
        stamp = datetime.now(timezone.utc) - timedelta(seconds=0 if stop else 1)
        event = {'type':'AgentSessionEvent','action':'prompted','webhookTimestamp':int(time.time()*1000),
                 'oauthClientId':'fixture-client','appUserId':'fixture-app','organizationId':'fixture-org',
                 'agentSession':{'id':name}, 'agentActivity':{'id':name+('-stop' if stop else ''),
                 'createdAt':stamp.isoformat(), 'content':{'type':'prompt','body':'synthetic diagnostic'}}}
        if stop: event['agentActivity']['signal'] = 'stop'
        raw = json.dumps(event).encode()
        assert service.receive(raw,hmac.new(b'fixture-secret',raw,hashlib.sha256).hexdigest())[0] == 200

    class Client(UnityIdentityClient):
        after_sample = None
        def session_probe(self):
            sample = super().session_probe()
            if self.after_sample:
                callback, self.after_sample = self.after_sample, None
                callback()
            return sample
    client = Client()
    inspector = RequestSessionInspector(store,client)

    def case(name, overrides, differences, stop_during=False):
        with service.db:
            service.sessions.ensure(name, 'fixture-task-'+name)
            service.sessions.set_target(name,target)
        receive(name)
        with service.db:
            request = store.enqueue('fixture-org:prompted:'+name)
            owner = store.acquire('session-diagnostic')
        assert owner['request_id'] == request
        inspector.bind(request, owner['token'], {**expected, **overrides})
        if stop_during: client.after_sample = lambda: receive(name, True)
        result = inspector.inspect(request, owner['token'])
        record(name,result)
        check_case(result, {'source':'match','editor':'match','session':'match',
                            'request_current':'match', **differences})
        if stop_during:
            assert result['checks']['session'] == 'match'
            assert result['checks']['request_current'] == 'mismatch'
            try: inspector.inspect(request, owner['token'])
            except ValueError: record('stopped_owner_rejected', {'rejected':True})
            else: raise AssertionError('Stopped owner inspected')
        if args.mode == 'edit-mode': assert result.get('observation_status') == 'edit_mode'
        with service.db:
            # This harness dispatched only synchronous read-only probes, no actions.
            released = store.release(request, owner['token'])
        record(name+'_released', {'state':released})

    try:
        if args.mode == 'authenticated':
            case('correct', {}, {})
            case('wrong_player', {'player_id':expected['player_id'] % 4294967295 + 1}, {'session':'mismatch'})
            route = '0'*64 if expected['route_sha256'] != '0'*64 else '1'*64
            case('wrong_route', {'route_sha256':route}, {'session':'mismatch'})
            mvid = '00000000-0000-0000-0000-000000000000'
            assert expected['hot_mvid'] != mvid
            case('wrong_module', {'hot_mvid':mvid}, {'editor':'mismatch'})
            case('stop_during_sample', {}, {'request_current':'mismatch'}, stop_during=True)
        else:
            case('edit_mode', {}, {'editor':'mismatch','session':'unknown'})
        assert source_snapshot(args.project) == before
        assert service.db.execute('SELECT count(*) FROM controller_actions').fetchone()[0] == 0
        record('cleanup', {'source_unchanged':True, 'actions_dispatched':False,
                          'states':[x['state'] for x in store.status()]})
    finally:
        service.close()


if __name__ == '__main__':
    main()
