"""Opt-in supervised fixture, NOT a deployed worker or automatic unit test.

Prepare the panel and inspect it first, following the matching scenario. This
script only drives that panel. It creates a NEW private synthetic queue; network
delivery is mocked. Failures keep its reservation held for manual investigation.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from farmqa_identity import source_snapshot
from farmqa_unity_identity import UnityIdentityClient
from linear_farmqa import BridgeService


def main():
    if not __debug__:
        raise RuntimeError('Assertions must be enabled for this supervised test')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch('[a-f0-9]{32}', args.run_id):
        raise ValueError('Invalid fixture run id')
    args.output.mkdir(parents=True, exist_ok=False)
    trace = []

    def record(label, value):
        trace.append({'label': label, 'recorded_at_ms': int(time.time()*1000), 'value': value})
        (args.output/'trace.json').write_text(json.dumps(trace, indent=2), encoding='utf-8')
        print(label, flush=True)
        return value

    client = UnityIdentityClient()
    client.read('mcpforunity://custom-tools')
    instances = client.read('mcpforunity://instances')['instances']
    assert len(instances) == 1 and instances[0]['id'] == args.instance
    client.select(args.instance)
    before = record('source_before', source_snapshot(args.project))
    editor = record('editor', client.probe())
    assert Path(editor['dataPath']).parent.resolve() == args.project.resolve()
    assert editor['isPlaying'] is True and editor['isCompiling'] is False and editor['isUpdating'] is False
    session = record('session', client.session_probe())
    assert session.get('authenticated') is False and session.get('transport_connected') is False
    code = (ROOT/'tests/probes/pointer-cancellation.cs.txt').read_text(encoding='utf-8')

    def probe(op):
        assert op in ('status', 'start', 'compete', 'cancel', 'recovery', 'cleanup')
        result = client._payload(client._rpc('tools/call', {'name': 'execute_code', 'arguments': {
            'action': 'execute', 'code': code.replace('__OP__', op).replace('__RUN_ID__', args.run_id),
            'safety_checks': True}}), 'content')['result']
        assert result['run_id'] == args.run_id and result['schema_version'] == 1
        return record(op, result)

    def wait(predicate):
        # Scheduling budget, not an end-to-end deadline: the existing MCP client
        # gives each in-flight HTTP call a separate 20-second timeout.
        end = time.monotonic() + 15
        while time.monotonic() < end:
            value = probe('status')
            if predicate(value):
                return value
            time.sleep(.1)
        raise TimeoutError('Fixture observation timed out; reservation stays held')

    initial = probe('status')
    assert initial['quiescent'] is True and initial['original'] is None and initial['events'] == []
    db_path = args.output/'synthetic.sqlite3'
    bridge = Mock(thread_id='synthetic-task')
    send = Mock(return_value={'success': True, 'agentActivity': {'id': 'synthetic-reply'}})
    service = BridgeService(db_path, 'fixture-secret', 'fixture-client', 'fixture-app', 'fixture-org', send, bridge=bridge)
    store = service.controller
    now = datetime.now(timezone.utc)
    target = {'repository': str(args.project.resolve()), 'requested_ref': 'HEAD',
              'commit_sha': before['commit_sha'], 'server_environment': 'offline-login-fixture',
              'selected_at': int(time.time()*1000), 'source': 'local_operator',
              'verification': 'not_verified_in_unity'}

    def receive(session_id, activity, stop=False):
        event = {'type': 'AgentSessionEvent', 'action': 'prompted',
                 'webhookTimestamp': int(time.time()*1000), 'oauthClientId': 'fixture-client',
                 'appUserId': 'fixture-app', 'organizationId': 'fixture-org',
                 'agentSession': {'id': session_id}, 'agentActivity': {
                     'id': activity, 'createdAt': (now if stop else now-timedelta(seconds=1)).isoformat(),
                     'content': {'type': 'prompt', 'body': 'synthetic fixture'}}}
        if stop:
            event['agentActivity']['signal'] = 'stop'
        raw = json.dumps(event).encode()
        result = service.receive(raw, hmac.new(b'fixture-secret', raw, hashlib.sha256).hexdigest())
        assert result[0] == 200, result
        return result

    for session_id in ('pointer-A', 'pointer-B'):
        with service.db:
            service.sessions.ensure(session_id, 'synthetic-task-'+session_id)
            service.sessions.set_target(session_id, target)
        receive(session_id, session_id)
        with service.db:
            store.enqueue('fixture-org:prompted:'+session_id)

    def acquire(owner):
        with service.db:
            return store.acquire(owner)

    def contender():
        result = subprocess.run([sys.executable, str(ROOT/'tools/farmqa_worker.py'),
                                 '--db', str(db_path), '--seconds', '0'],
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, 'Competing worker process failed'
        value = json.loads(result.stdout)
        record('competing_process', value)
        assert value['outcome'] == 'blocked'

    owner = acquire('supervised-pointer-fixture')
    assert owner['session_id'] == 'pointer-A'
    record('queue_acquired', store.status())  # Never record private ownership token.
    contender()
    probe('start')
    pressed = wait(lambda value: value['events'] == ['down'] and value['held'] is True)
    assert pressed['busy'] is True and pressed['simulation_active'] is True
    second = probe('compete')['competitor']
    assert second['complete'] is True and second['result']['success'] is False
    assert second['result']['reason'].startswith('pointer busy:')
    record('synthetic_signed_stop', receive('pointer-A', 'pointer-stop', stop=True))
    assert store.cancelled(owner['request_id'], owner['token']) is True
    record('queue_stopping', store.status())
    contender()
    probe('cancel')
    stopped = wait(lambda value: value['original']['complete'] is True and value['quiescent'] is True)
    assert stopped['original']['result']['success'] is False
    assert stopped['original']['result']['reason'] == 'cancelled by caller'
    assert stopped['events'] == ['down', 'up']
    with service.db:
        assert store.release(owner['request_id'], owner['token']) == 'cancelled'
    record('queue_cancelled', store.status())
    owner_b = acquire('supervised-recovery-fixture')
    assert owner_b['session_id'] == 'pointer-B'
    probe('recovery')
    recovered = wait(lambda value: value['recovery']['complete'] is True and value['quiescent'] is True)
    assert recovered['recovery']['result']['success'] is True
    assert recovered['events'] == ['down', 'up', 'down', 'up', 'click']
    with service.db:
        assert store.release(owner_b['request_id'], owner_b['token']) == 'released'
    record('queue_released', store.status())
    cleanup = probe('cleanup')
    assert cleanup['fixture_present'] is False
    assert cleanup['new_console_errors'] == 0
    after = record('source_after', source_snapshot(args.project))
    assert before == after
    bridge.dispatch.assert_not_called()
    service.close()
    record('result', {'status': 'PASS', 'scope': 'supervised synthetic Stop and real fixture pointer',
                      'gameplay_actions': 0, 'production_worker_enabled': False})


if __name__ == '__main__':
    main()
