"""Run one inert controller wait. No game actions or abandoned-slot recovery."""
import argparse
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import time

from farmqa_controller import ControllerStore


def emit(**fields):
    print(json.dumps({'mode': 'inert', 'game_actions': 0, **fields}), flush=True)


def run_once(db_path, seconds=5):
    if (isinstance(seconds, bool) or not isinstance(seconds, (int, float))
            or not math.isfinite(seconds) or not 0 <= seconds <= 60):
        raise ValueError('Inert wait must be between 0 and 60 seconds')
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri()+'?mode=rw',
                                uri=True, timeout=1)) as db:
        db.row_factory = sqlite3.Row
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='controller_requests'").fetchone():
            raise ValueError('Controller queue has not been initialized')
        # The worker opens existing state only. Schema migration belongs to receiver.
        store = ControllerStore.__new__(ControllerStore)
        store.db = db
        with db:
            reservation = store.acquire('inert-worker')
            if reservation is None:
                busy = db.execute("SELECT 1 FROM controller_requests WHERE state IN ('active','cancel_requested')").fetchone()
                outcome = 'blocked' if busy else 'idle'
        if reservation is None:
            result = {'event': 'finished', 'outcome': outcome}
            emit(**result)
            return result

        request_id, token = reservation['request_id'], reservation['token']
        started = time.monotonic()
        emit(event='acquired', request_id=request_id)
        # No transaction spans a sleep: Stop must be able to acquire its write lock.
        # Errors deliberately do not release in finally. Unknown state keeps ownership.
        while True:
            if store.cancelled(request_id, token):
                break
            remaining = seconds - (time.monotonic() - started)
            if remaining <= 0:
                break
            time.sleep(min(.1, remaining))
        # The only work was the synchronous wait above; it has now ended.
        # release rechecks cancellation atomically with the ownership transition.
        with db:
            outcome = store.release(request_id, token)
        result = {'event': 'finished', 'request_id': request_id,
                  'outcome': outcome, 'elapsed_seconds': round(time.monotonic()-started, 3)}
        emit(**result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True,
                        help='Explicit path to an existing controller ledger')
    parser.add_argument('--seconds', type=float, default=5)
    args = parser.parse_args()
    run_once(args.db, args.seconds)


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        # No raw exception, paths, request content, or token in operator output.
        emit(event='error', error_type=type(exc).__name__,
             outcome='unconfirmed', ownership='inspect_ledger')
        raise SystemExit(1)
