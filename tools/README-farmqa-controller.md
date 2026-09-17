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

## Future worker contract

`ControllerStore(db)` uses `sqlite3.Row` and caller-managed transactions. Acquire
and release must commit before relying on their result. Autocommit connections
must explicitly `BEGIN IMMEDIATE`; a mutation without a transaction is rejected.

```python
with db:
    reservation = ControllerStore(db).acquire('qa-worker')
```

Only one request can be active globally. An active/cancel-requested slot survives
restart indefinitely. The returned token must remain private to its owner; the
database stores a hash. No worker is installed in this increment. There is no
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
is made yet.

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
