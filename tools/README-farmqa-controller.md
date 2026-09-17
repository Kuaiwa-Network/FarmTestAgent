# FarmQA controller reservations

This is the persistent scheduling layer for one shared QA controller. It does
not execute Unity/computer actions, verify the loaded build, or automatically
interrupt Codex. The bridge remains a chat service. Normal messages do not
automatically enter this queue.

Use one deployment database for one controller and one Linear workspace.
All workers must use that same database. Copying a database creates an independent
queue; it must not be used to drive the same physical controller concurrently.

## Operator commands

From the deployment repository, inspect the initialized queue:

```powershell
python tools/farmqa_controller.py status
```

To prepare a reservation, first pin the target with the existing `set-target`
command in README-farmqa.md, then receive a new Linear message. Explicitly enqueue
that accepted message's event key:

```powershell
python tools/farmqa_controller.py enqueue --event '<organization>:prompted:<activity-id>'
```

The event must already exist in the authenticated receiver ledger. An unpinned,
stopped, or uncertain event is rejected. The request copies the event's original
target; changing the session default does not alter it. Repeating enqueue returns
the same reservation ID. Enqueue does not start a worker or a game action.
`--db` selects an existing ledger explicitly; the command never creates one.
Status opens SQLite read-only and omits tokens, prompt bodies and worker names.

## Inert worker

The standalone worker consumes at most one existing reservation, waits, then
exits. Select the database explicitly:

```powershell
python tools/farmqa_worker.py --db .local/farmqa/events.sqlite3 --seconds 5
```

Only use this on reservations intentionally queued for the inert test. A released
request cannot be replayed as gameplay. The worker opens an existing database;
it neither initializes schema nor queues requests. Wait duration must be finite
and between 0 and 60 seconds. Default: 5 seconds. Stop is checked every 100 ms;
SQLite operations time out after 1 second. These settings are not a real-time
cancellation guarantee under database contention or OS scheduling delays.

Output is newline-delimited JSON with `mode: inert`, `game_actions: 0`, request
ID and an outcome. `idle` means no queue; `blocked` means a reservation is held;
`released` means the inert wait ended; `cancelled` means Stop was observed during
ownership. These outcomes exit zero because the one-shot operation was handled;
automation must inspect the outcome, not equate exit zero with a QA pass.
Errors exit nonzero and report `unconfirmed` with the exception class only.

There is no Unity/computer/model/network operation, command execution adapter,
background worker, or scheduled service. Acquisition commits before waiting;
the wait ends before release. A killed process, Ctrl+C, database error or lost
owner token leaves a reservation held. A fresh worker refuses takeover. This
verifies safe crash persistence, not automatic crash recovery. Inspect the
ledger and preserve the hold; there is no force-release/recovery command yet.

## Worker contract

For current Editor/source observations use the separate
[read-only identity command](README-farmqa-identity.md). It appends diagnostics
without acquiring or releasing a reservation; it cannot authorize gameplay.

`ControllerStore(db)` uses `sqlite3.Row` and caller-managed transactions. Acquire
and release must commit before relying on their result. Autocommit connections
must explicitly `BEGIN IMMEDIATE`; a mutation without a transaction is rejected.

```python
with db:
    reservation = ControllerStore(db).acquire('qa-worker')
```

Only one request can be active globally. An active/cancel-requested slot survives
restart indefinitely. The returned token must remain private to its owner; the
database stores a hash. Only the inert worker above exists. There is no
expiry, automatic takeover, token recovery, or force-unlock command.

Authenticated Linear Stop cancels queued requests at/before its source timestamp
in that session. For active ownership it sets `cancel_requested` and retains the
slot. The worker checks `cancelled(request_id, token)`, stops its own bounded
actions, verifies quiescence, then calls `release(request_id, token)` in a
transaction. A Stop between check and release still yields `cancelled`.
`released` means reservation ownership ended, not that QA passed. Do not hold a
SQLite transaction while executing actions, because that would block Stop.

If an owner disappears, keep the slot held and inspect the actual controller.
Do not edit the ledger to force availability. Operator recovery and a physical
action adapter must be designed and tested before gameplay is enabled. These
reservation APIs do not prevent a separate task from directly calling Unity or
computer tools. No claim of physical exclusivity or successful action cancellation
is made for a production adapter yet. A later supervised
[fixture check](../reports/2026-09-17-farmqa-pointer-cancellation/report.md) verified
the real driver's busy rejection, cancellation and quiescence using a separate
synthetic queue. Its opt-in replay harness lives under `tests/probes/`, not as a
deployed worker. Direct MCP/OS bypass, stale-owner fencing and crash/lost-response
recovery remain unresolved; do not automatically enable game actions from it.

A subsequent [fixture adapter](README-farmqa-fixture-adapter.md) adds a
`controller_actions` table and release interlock. It has verified retired-ID
rejection and injected lost-response reconciliation on that panel, with no
production upgrade. The receiver constructor initializes this schema when the
updated code is explicitly run; it does not automatically execute actions.
Pending/uncertain action rows block release even by another cooperating caller.
Read the adapter's scope/recovery contract before using it. General game-action
ownership and actual lost-owner recovery are not established by the fixture test.

## Verification and rollback

Run `python -m unittest discover -s tests -p 'test_*.py' -v`.
Tests use synthetic events/temporary databases and mocked external delivery.
The two-process test verifies SQLite reservation competition, not game control.
Read the dated controller report for migration/deployment evidence.

Before a receiver restart, retain a private SQLite backup and verify no active
delivery operation needs reconciliation. Stop only the identified receiver child;
its existing supervisor restarts it, preserving the tunnel. To roll back this
increment, restore the preceding receiver code while the queue is empty. Do not
roll back with active reservations: older code cannot propagate Stop into them.
Keep all database/config backups under ignored `.local/` and out of reports/Git.
