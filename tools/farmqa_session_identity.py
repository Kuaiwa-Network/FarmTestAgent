"""Standalone read-only session comparison. Never a gameplay execution permit."""
import argparse
import json
import math
from pathlib import Path
import re
import time
from farmqa_unity_identity import UnityIdentityClient
from farmqa_identity import project_matches, source_snapshot


def evaluate(sample, expected, *, now_ms=None):
    result = {'session_match':'unknown', 'verdict':'BLOCKED', 'execution_enabled':False}
    if not isinstance(sample,dict) or not isinstance(expected,dict): return result
    stamp = sample.get('observed_at_ms')
    now_ms = time.time()*1000 if now_ms is None else now_ms
    def uint(value): return type(value) is int and 0 < value <= 4294967295
    def sha(value): return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None
    if not (type(sample.get('schema_version')) is int and sample['schema_version'] == 1
            and sample.get('status') == 'observed'
            and type(stamp) in (int,float) and math.isfinite(stamp)
            and type(now_ms) in (int,float) and math.isfinite(now_ms)
            and 0 <= now_ms-stamp <= 10000
            and all(sample.get(key) is True for key in
                    ('is_playing','authenticated','transport_connected','objects_stable'))
            and uint(sample.get('generation_before'))
            and type(sample.get('generation_after')) is int
            and sample['generation_before'] == sample['generation_after']
            and uint(sample.get('player_id')) and uint(expected.get('player_id'))
            and sha(sample.get('route_sha256')) and sha(expected.get('route_sha256'))):
        return result
    result['session_match'] = 'match' if all(sample[k] == expected[k]
                                          for k in ('player_id','route_sha256')) else 'mismatch'
    return result


def inspect_session(instance, project, expected, client=None):
    """Select and recheck the exact Editor. No queue or production DB mutations."""
    client = client or UnityIdentityClient()
    result = {'session_match':'unknown','verdict':'BLOCKED','execution_enabled':False}
    try:
        before = source_snapshot(project)
        client.read('mcpforunity://custom-tools')
        def exact_instance():
            entries = client.read('mcpforunity://instances')['instances']
            return len(entries) == 1 and entries[0]['id'] == instance
        if not exact_instance(): return result
        client.select(instance)
        if not project_matches(client.read('mcpforunity://project/info').get('projectRoot'),project):
            return result
        sample = client.session_probe()
        # The probe checks live busy flags itself; a stale advisory resource is
        # never turned into readiness. This utility does not authorize actions.
        if (not exact_instance()
                or not project_matches(client.read('mcpforunity://project/info').get('projectRoot'),project)
                or before != source_snapshot(project)):
            return result
        result = evaluate(sample,expected)
        status = sample.get('status') if isinstance(sample,dict) else None
        if status in ('observed','edit_mode','busy','missing_objects','unsupported_schema','unavailable'):
            result['observation_status'] = status
    except Exception as exc:
        result['error_type'] = type(exc).__name__
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance',required=True)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--expected',type=Path,help='Private JSON: player_id and exact route_sha256')
    args=parser.parse_args()
    expected=json.loads(args.expected.read_text(encoding='utf-8')) if args.expected else None
    print(json.dumps(inspect_session(args.instance,args.project,expected),indent=2))
    return 2


if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'verdict':'BLOCKED','execution_enabled':False,'error_type':type(exc).__name__}))
        raise SystemExit(1)
