"""Append fresh read-only Editor identity diagnostics for a controller request.

Not an execution permit: loaded-commit provenance and server identity are not
supported by the current probe, so every result remains BLOCKED for gameplay.
"""
import argparse
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import uuid

from farmqa_controller import checked_target
from farmqa_unity_identity import UnityIdentityClient


def source_snapshot(repository):
    root = Path(repository).resolve(strict=True)
    def git(*args):
        return subprocess.run(['git','--no-optional-locks','-c','core.fsmonitor=false',
                               '-C',str(root),*args], check=True, capture_output=True,
                              timeout=10).stdout.decode('utf-8')
    if Path(git('rev-parse','--show-toplevel').strip()).resolve() != root:
        raise ValueError('Target must be the repository root')
    head = git('rev-parse','--verify','HEAD').strip()
    if not re.fullmatch('[0-9a-f]{40}', head): raise ValueError('Unknown source revision')
    # No rename folding: each entry is exactly XY + path + NUL, including Unicode.
    status = git('status','--porcelain=v1','-z','--untracked-files=all','--no-renames')
    if len(status) > 1024*1024: raise ValueError('Source status exceeds bound')
    dirty = []
    for entry in filter(None, status.split('\0')):
        relative = entry[3:]
        path = root/relative
        digest = None
        # Never follow dirty symlinks/junctions outside the checkout or read devices.
        if path.resolve().is_relative_to(root) and path.is_file() and not path.is_symlink():
            if path.stat().st_size > 16*1024*1024: raise ValueError('Dirty file exceeds hash bound')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        dirty.append({'path':relative, 'status':entry[:2], 'sha256':digest})
    index_hash = hashlib.sha256(git('ls-files','--stage','-z').encode('utf-8')).hexdigest()
    return {'repository':str(root), 'commit_sha':head, 'dirty':dirty,
            'index_sha256':index_hash}


def ready(state, instance):
    """Require current, explicitly idle Edit Mode; missing booleans never pass."""
    try:
        observed = state['observed_at_unix_ms']
        return (state['schema_version'] == 'unity-mcp/editor_state@2'
                and type(observed) in (int,float) and math.isfinite(observed)
                and 0 <= time.time()*1000-observed <= 10000
                and state['unity']['instance_id'] == instance
                and state['staleness']['is_stale'] is False
                and state['advice']['ready_for_tools'] is True
                and all(state['editor']['play_mode'][key] is False
                        for key in ('is_playing','is_paused','is_changing'))
                and state['compilation']['is_compiling'] is False
                and state['compilation']['is_domain_reload_pending'] is False
                and state['assets']['is_updating'] is False
                and state['tests']['is_running'] is False)
    except (KeyError, TypeError):
        return False


def safe_text(value, limit=4096):
    return value if (isinstance(value,str) and 0 < len(value) <= limit
                     and not any(ord(c)<32 for c in value)) else None


def project_matches(value, expected):
    return bool(safe_text(value) and Path(value).resolve() == Path(expected).resolve())


def collect(target, instance, build_target, client):
    result = {'checks':{key:'unknown' for key in ('editor_ready','project','source_commit',
        'source_clean','source_stable','build_target','loaded_assemblies','loaded_source',
        'server_environment')}}
    checks = result['checks']
    try:
        result['source_before'] = source_snapshot(target['repository'])
        client.read('mcpforunity://custom-tools')
        instances = client.read('mcpforunity://instances')['instances']
        if len(instances) != 1 or instances[0]['id'] != instance:
            raise ValueError('Expected one exact Editor instance')
        client.select(instance)
        before = client.read('mcpforunity://editor/state')
        if not ready(before, instance): return result
        info = client.read('mcpforunity://project/info')
        probe = client.probe()
        after = client.read('mcpforunity://editor/state')
        result['source_after'] = source_snapshot(target['repository'])
        result['editor'] = {key:safe_text(probe.get(key)) for key in
                            ('unityVersion','platform','buildTarget','dataPath')}
        result['editor']['instance'] = instance
        result['editor']['observed_before_ms'] = before['observed_at_unix_ms']
        observed_after = after.get('observed_at_unix_ms')
        result['editor']['observed_after_ms'] = observed_after if (
            type(observed_after) in (int,float) and math.isfinite(observed_after)) else None
        result['editor']['play_mode_off'] = probe.get('isPlaying') is False
        assemblies = probe.get('assemblies')
        expected = {'HotUpdate','AOTScripts','Nova.Runtime','MCPForUnity.Editor'}
        observed = []
        if isinstance(assemblies,list):
            for assembly in assemblies:
                name, mvid = assembly.get('name'), assembly.get('moduleMvid')
                if name in expected and isinstance(mvid,str) and re.fullmatch(
                        '[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', mvid):
                    observed.append({'name':name,'module_mvid':mvid.lower()})
        result['editor']['assemblies'] = observed
        if len(observed) == 4 and {a['name'] for a in observed} == expected:
            checks['loaded_assemblies'] = 'observed'
        if (ready(after, instance)
                and before['unity'] == after['unity']
                and all(probe.get(key) is False for key in
                        ('isPlaying','isPlayingOrWillChangePlaymode','isCompiling','isUpdating'))
                and probe.get('scene',{}).get('isDirty') is False):
            checks['editor_ready'] = 'match'
        checks['project'] = 'match' if (project_matches(info.get('projectRoot'),target['repository'])
            and project_matches(probe.get('dataPath'),Path(target['repository'])/'Assets')) else 'mismatch'
        checks['build_target'] = 'match' if (probe.get('buildTarget') == build_target
            and info.get('platform') == build_target) else 'mismatch'
        first, last = result['source_before'], result['source_after']
        checks['source_commit'] = 'match' if first['commit_sha'] == last['commit_sha'] == target['commit_sha'] else 'mismatch'
        checks['source_clean'] = 'match' if not first['dirty'] and not last['dirty'] else 'mismatch'
        checks['source_stable'] = 'match' if first == last else 'mismatch'
        # These are deliberately UNKNOWN. A requested environment is not observed
        # session identity; an MVID or checkout SHA is not loaded-build provenance.
    except Exception as exc:
        result['error_type'] = type(exc).__name__
    return result


def inspect_request(db_path, request_id, instance, build_target, client=None):
    if not safe_text(instance,256) or not safe_text(build_target,128):
        raise ValueError('Explicit instance and build target are required')
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri()+'?mode=rw',
                                uri=True, timeout=1)) as db:
        db.row_factory = sqlite3.Row
        row = db.execute('SELECT target_json,state FROM controller_requests WHERE request_id=?',
                         (request_id,)).fetchone()
        if not row or row['state'] not in ('queued','active'):
            raise ValueError('A queued or active request is required')
        target = checked_target(row['target_json'])
        started = time.time()
        result = collect(target, instance, build_target, client or UnityIdentityClient())
        result.update(schema_version=1, observation_id=str(uuid.uuid4()), request_id=request_id,
                      target=target, expected={'instance':instance,'build_target':build_target},
                      started_at=started, finished_at=time.time(), verdict='BLOCKED',
                      execution_enabled=False, mode='read_only_identity')
        # No DB transaction spans external reads. This lock rechecks Stop/target
        # before appending evidence. It never changes the reservation itself.
        with db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT target_json,state FROM controller_requests WHERE request_id=?',
                                 (request_id,)).fetchone()
            result['checks']['request_current'] = 'match' if (current and
                current['state'] in ('queued','active') and current['target_json'] == row['target_json']) else 'mismatch'
            db.execute('''CREATE TABLE IF NOT EXISTS controller_identity_observations (
                observation_id TEXT PRIMARY KEY, request_id TEXT NOT NULL,
                created_at REAL NOT NULL, result_json TEXT NOT NULL)''')
            db.execute('INSERT INTO controller_identity_observations VALUES (?,?,?,?)',
                       (result['observation_id'],request_id,result['finished_at'],json.dumps(result)))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--request', required=True)
    parser.add_argument('--instance', required=True)
    parser.add_argument('--build-target', required=True)
    parser.add_argument('--endpoint', default='http://127.0.0.1:9090/mcp')
    args = parser.parse_args()
    result = inspect_request(args.db,args.request,args.instance,args.build_target,
                             UnityIdentityClient(args.endpoint))
    print(json.dumps(result,indent=2))
    return 2  # BLOCKED is a diagnostic result, never a successful gameplay gate.


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps({'verdict':'BLOCKED','execution_enabled':False,
                          'error_type':type(exc).__name__}))
        raise SystemExit(1)
