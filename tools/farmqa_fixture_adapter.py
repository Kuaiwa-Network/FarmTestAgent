"""Explicit, fixture-only controller adapter. No CLI, daemon or gameplay permit."""
import base64
import json
import math
from pathlib import Path
import re
import time
import uuid

from farmqa_identity import source_snapshot
from farmqa_unity_identity import UnityIdentityClient


def checked_binding(value):
    fields = ('instance', 'project', 'commit_sha', 'hot_mvid', 'build_target', 'run_id')
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('Exact fixture binding required')
    if any(not isinstance(value[k], str) or not value[k] or len(value[k]) > 4096 or
           any(ord(c) < 32 for c in value[k]) for k in fields):
        raise ValueError('Invalid fixture binding')
    if (not re.fullmatch('[0-9a-f]{40}', value['commit_sha']) or
        not re.fullmatch('[0-9a-f]{32}', value['run_id']) or
        not re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', value['hot_mvid']) or
        value['build_target'] != 'StandaloneWindows64' or not Path(value['project']).is_absolute()):
        raise ValueError('Unsupported fixture target')
    return dict(value)


def checked_observation(raw, action_id, binding):
    if not isinstance(raw, dict): raise ValueError('Missing action observation')
    stamp = raw.get('observed_at_ms')
    if (type(raw.get('schema_version')) is not int or raw['schema_version'] != 1 or raw.get('action_id') != action_id or
        raw.get('run_id') != binding['run_id'] or type(stamp) not in (int, float) or
        not math.isfinite(stamp) or not 0 <= time.time()*1000-stamp <= 10000):
        raise ValueError('Stale or mismatched action observation')
    flags = ('started', 'completed', 'quiescent', 'closed', 'cancel_requested')
    if any(type(raw.get(k)) is not bool for k in flags): raise ValueError('Unknown action state')
    if raw['closed'] and (not raw['completed'] or not raw['quiescent']):
        raise ValueError('Inconsistent closure')
    if not raw['started'] and not raw['cancel_requested']:
        raise ValueError('Unknown unstarted action')
    events = raw.get('events')
    if not isinstance(events, list) or len(events) > 32 or any(x not in ('down','up','click') for x in events):
        raise ValueError('Invalid fixture events')
    if raw.get('success') is not None and type(raw['success']) is not bool:
        raise ValueError('Invalid pointer result')
    if type(raw.get('new_console_errors')) is not int or raw['new_console_errors'] < 0:
        raise ValueError('Unknown console state')
    return {k: raw[k] for k in ('schema_version','action_id','run_id','observed_at_ms',
                               *flags,'events','success','new_console_errors')}


class FixtureClient(UnityIdentityClient):
    """Only the fixed fixture protocol; no operator-supplied code or coordinates."""
    def validate(self, binding):
        source = source_snapshot(binding['project'])
        if source['commit_sha'] != binding['commit_sha'] or source['dirty']:
            raise ValueError('Pinned source mismatch')
        self.read('mcpforunity://custom-tools')
        instances = self.read('mcpforunity://instances')['instances']
        if len(instances) != 1 or instances[0]['id'] != binding['instance']:
            raise ValueError('Ambiguous or mismatched Unity instance')
        self.select(binding['instance'])
        state = self.read('mcpforunity://editor/state')
        if state.get('tests', {}).get('is_running') is not False:
            raise ValueError('Editor test state unknown or busy')
        # Project/module/Play Mode/login checks also run inside the action call.

    def exchange(self, op, action_id, binding):
        binding = checked_binding(binding)
        if op not in ('start','status','cancel','close') or not re.fullmatch('[a-f0-9]{32}', action_id):
            raise ValueError('Unsupported fixture operation')
        self.select(binding['instance'])
        code = (Path(__file__).resolve().parents[1]/'tests/probes/fixture-adapter.cs.txt').read_text(encoding='utf-8')
        for key, value in {'OP':op, 'ACTION_ID':action_id, 'RUN_ID':binding['run_id'],
                           'PROJECT_B64':base64.b64encode(binding['project'].encode()).decode(),
                           'MVID':binding['hot_mvid'], 'BUILD':binding['build_target']}.items():
            code = code.replace('__'+key+'__',value)
        result = self._payload(self._rpc('tools/call', {'name':'execute_code', 'arguments':{
            'action':'execute','code':code,'safety_checks':True}}), 'content')
        return result['result']


class FixtureAdapter:
    """One synchronous caller per connection. Durable intent, no start retry.

    Uses the current reservation token; does not acquire, reclaim or recover it.
    The caller polls observe to propagate Stop. Only finish may release a slot.
    """
    def __init__(self, store, client):
        self.store, self.db, self.client = store, store.db, client

    def _owner(self, request_id, token, active_only=False):
        row = self.store._owned(request_id, token)
        if row['state'] not in (('active',) if active_only else ('active','cancel_requested')):
            raise ValueError('Reservation is no longer an active owner')
        return row

    def _entry(self):
        if self.db.in_transaction: raise ValueError('Do not hold a transaction across adapter calls')

    _binding = staticmethod(checked_binding)
    _observation = staticmethod(checked_observation)

    def _target(self, row, binding):
        target = json.loads(row['target_json'])
        if (Path(target['repository']).resolve() != Path(binding['project']).resolve() or
            target['commit_sha'] != binding['commit_sha'] or
            target['server_environment'] != 'offline-login-fixture'):
            raise ValueError('Reservation is not pinned to this offline fixture')

    def start(self, request_id, token, binding):
        self._entry()
        binding = self._binding(binding)
        row = self._owner(request_id, token, active_only=True)
        self._target(row, binding)
        if self.db.execute('SELECT 1 FROM controller_actions WHERE request_id=?',(request_id,)).fetchone():
            raise ValueError('This reservation already attempted an action')
        self.client.validate(binding)
        with self.db:
            self.store._write_lock()
            current = self._owner(request_id, token, active_only=True)
            if current['target_json'] != row['target_json']:
                raise ValueError('Pinned target changed during validation')
            self._target(current, binding)
            self.db.execute('INSERT INTO controller_actions(request_id,action_id,binding_json,state) VALUES(?,?,?,?)',
                            (request_id,uuid.uuid4().hex,json.dumps(binding),'pending'))
        return self._exchange(request_id, token, 'start')

    def _exchange(self, request_id, token, op):
        owner = self._owner(request_id, token)
        if op == 'start' and owner['state'] == 'cancel_requested':
            with self.db:
                self.db.execute('UPDATE controller_actions SET cancel_attempted=1 WHERE request_id=?',(request_id,))
            op = 'cancel'
        row = self.db.execute('SELECT * FROM controller_actions WHERE request_id=?',(request_id,)).fetchone()
        if not row: raise ValueError('No persisted action')
        binding = json.loads(row['binding_json'])
        try:
            raw = self.client.exchange(op, row['action_id'], binding)
            result = self._observation(raw, row['action_id'], binding)
            with self.db:
                self.store._write_lock()
                self._owner(request_id, token)
                self.db.execute('UPDATE controller_actions SET state=?,observation_json=? WHERE request_id=?',
                                ('closed' if result['closed'] else 'pending',json.dumps(result),request_id))
            return result
        except BaseException:
            # Even KeyboardInterrupt/process loss must not make the next worker
            # assume an already-dispatched remote action stopped.
            with self.db:
                self.db.execute("UPDATE controller_actions SET state='uncertain' WHERE request_id=?",(request_id,))
            raise

    def observe(self, request_id, token):
        self._entry()
        with self.db:
            self.store._write_lock()
            owner = self._owner(request_id, token)
            row = self.db.execute('SELECT * FROM controller_actions WHERE request_id=?',(request_id,)).fetchone()
            if not row: raise ValueError('No persisted action')
            previous = json.loads(row['observation_json']) if row['observation_json'] else {}
            # Attempt is not delivery. Exact-action cancel is idempotent on Unity
            # (including a tombstone before start), so resend until acknowledged.
            cancel = owner['state'] == 'cancel_requested' and previous.get('cancel_requested') is not True
            if cancel:
                self.db.execute('UPDATE controller_actions SET cancel_attempted=1 WHERE request_id=?',(request_id,))
        return self._exchange(request_id, token, 'cancel' if cancel else 'status')

    def finish(self, request_id, token):
        result = self.observe(request_id, token)
        if not result['completed'] or not result['quiescent']:
            raise ValueError('Exact action is not quiescent')
        if not result['closed']:
            result = self._exchange(request_id, token, 'close')
        if not result['closed'] or not result['quiescent']:
            raise ValueError('Action closure unconfirmed')
        with self.db:
            self.store._write_lock()
            self._owner(request_id, token)
            state = self.store.release(request_id, token)
        return {**result, 'reservation_state':state}
