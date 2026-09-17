# FarmQA inert worker — 2026-09-17

Outcome: **PASS for inert process cancellation and safe crash persistence.**
Gameplay, physical controller exclusivity, and automatic active-Codex
interruption remain unverified/disabled.

## Scope and implementation

Built on merged PR #6 (`9a59451`) in `codex/farmqa-inert-worker`, isolated from
the running receiver. Python standard library only; tests ran on Windows with
Python 3.14.3. The standalone CLI explicitly opens one existing controller DB,
claims at most one queued request, commits, then performs only a synchronous
bounded wait. Default wait is 5 seconds, accepted range 0–60, Stop polling 100 ms,
SQLite timeout 1 second. There are no network/model/game/tool actions.

Normal completion releases the reservation; cancellation releases as cancelled.
Errors or process death do not release ownership. A new worker encountering
that active slot reports blocked. No lease expiry, force-unlock, worker restart
service or automatic token recovery is introduced. Output contains allowlisted
metadata only; never prompt text, target/account data or reservation tokens.

## Verification

Nine initial worker tests failed before the worker existed. Final full suite:
**104 tests passed**, including 11 worker tests plus 93 existing tests.
The worker tests launch actual Python subprocesses and use temporary SQLite
databases with signed synthetic events; external Linear/Codex delivery is mocked.

- The requested wait actually elapses before release; only one FIFO request is
  consumed, and another remains queued.
- A competing worker reports blocked while the first owns the slot.
- Signed Stop ends the active wait, releases as cancelled, then the next
  session can run. Another session's Stop leaves the active worker waiting.
- Forced subprocess termination followed by receiver restart preserves
  active ownership. A replacement worker remains blocked and queued work
  remains queued; no earlier request is replayed.
- A held exclusive database lock makes the worker fail with an unconfirmed
  outcome after its SQLite timeout; ownership remains active.
- Invalid/nonfinite duration, missing DB/schema, empty queues and output
  redaction are verified. The worker never creates an accidental database.

A separate recorded fixture run observed cancellation-to-process-exit in
0.022 seconds. This is one local observation, not a production SLA. Its
subsequent request released normally; after a fresh fixture's forced process
exit, states remained active/queued and a replacement reported blocked. See
[redacted process evidence](evidence/process-verification.json).

Independent read-only review found no blocking implementation issues. Its
recommendations added elapsed-time and other-session Stop process assertions.

## Deployment and limitations

This is a standalone operator utility, not a new background service. The live
receiver was not restarted, no production reservation was enqueued or consumed,
and no Linear messages were sent for this increment. No game/client/server
checkout was touched. Changes are committed locally; no PR push/merge performed.

Safe persistence after a crash is verified; restoring lost ownership is not.
An inert reservation does not prove cancellation of asynchronous game actions
or prevent direct Unity/computer tool use by another task. DB contention and OS
scheduling can delay Stop observation. No game worker should use this as evidence
that its own actions can safely stop. `released` is not a gameplay test verdict.

Next: implement read-only loaded-Editor identity validation against pinned
commit/environment, then design a bounded physical action adapter and recovery
procedure before any gameplay enablement. The prior live concurrent-chat Stop
check remains separate outstanding coverage.

Operator command and result meanings:
[controller guide](../../tools/README-farmqa-controller.md).
