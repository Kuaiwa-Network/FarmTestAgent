# FarmQA controller reservation queue — 2026-09-17

Scope: scheduling foundation of the user-approved shared QA controller design.
No Unity/computer/gameplay actions or new Codex tasks were executed.

## Implementation

Built in the isolated `codex/farmqa-controller-queue` worktree from `4175112`.
Python standard library only; tested on Windows with Python 3.14.3.
`ControllerStore` records FIFO requests and immutable event target snapshots.
Enqueue is an explicit local operator action; ordinary chat does not enqueue
game work. One reservation is enforced using a write transaction and unique
active-slot index. Tokens are private to the owner and hashed in SQLite.

Authenticated Linear Stop updates controller requests in the receiver's existing
transaction. Queued work is cancelled; active ownership stays reserved until the
same token releases it. Restart does not reclaim ownership. Wrong tokens fail;
duplicate enqueue/release are idempotent. `released` is not a QA verdict.
The CLI supports enqueue and redacted read-only status only.

## Validation

- 11 new tests first failed because the controller queue was absent; all passed
  after implementation. A separate autocommit regression failed before adding
  transaction enforcement. Final suite: **93 tests passed** (78 previous +15).
- Coverage includes two real Python processes competing for a slot, FIFO,
  target snapshot preservation, crash/restart ownership, authenticated Stop,
  queue/active cancellation distinction, other-session and newer-message
  isolation, duplicate Stop, wrong tokens, CLI behavior, malformed targets,
  status redaction, and autocommit rejection with explicit-transaction recovery.
- Migration on a private SQLite backup preserved exact pre-existing rows:
  17 events, 13 bridge jobs, 5 session routes, 3 Stop records. The new queue
  started empty. Synthetic signed events in that copy verified Stop retaining
  the active slot and the other session acquiring only after owner release.
  No real external sends occurred. See [evidence](evidence/migration.json).
- Independent code review found no blocking issue in this scope. Its suggestions
  prompted added organization-scope, CLI, malformed-target and autocommit tests.

## Deployment

Source commit `a238b2c` was fast-forwarded into the existing deployment branch
`codex/farmqa-session-routing`; no PR was pushed or merged. A private database
backup was retained before restarting only the verified receiver child through
its existing supervisor. The tunnel was not restarted. Final receiver PID 41756
had one listener at `127.0.0.1:8765` and verified FarmQA in Kuaiwa AI at startup.
All 17 event states and 5 session routes matched the predeployment snapshot.
The controller queue was initialized and empty; its CLI reports execution
disabled. The deployment checkout also passed all 93 tests.

Loopback and public HTTPS health returned 200, and unsigned webhooks returned
401. These diagnostic requests originated on this machine; no independent
external probe or new live mention is claimed. No controller reservation was
created in the live database. See [deployment evidence](evidence/deployment.json).

## Limitations and next increment

This is a scheduling reservation, not a machine-enforced lock on Unity/computer
tools. No physical worker, action adapter, loaded-build identity verifier, or
bounded game-action cancellation is installed. Stop isolation between real
concurrent Linear chats remains a supervised live check, separate from fixture
coverage here. Automatic interruption of an active Codex turn remains unavailable.

Use a single organization per deployment ledger. Existing bridge Stop/history
queries are session-scoped; the controller's Stop SQL is organization-scoped,
but this does not retrofit multi-workspace support into the earlier bridge.
An owner lost after a crash leaves a durable hold; operator recovery requires
actual controller quiescence evidence and is not implemented in this increment.

Next implement an inert worker that exercises cancellation/ownership without
game actions, then read-only actual Editor identity validation against pinned
targets. A physical action adapter remains gated on both checks. See
[operator instructions](../../tools/README-farmqa-controller.md) and
[design](../../docs/superpowers/specs/2026-09-17-controller-queue.md).
