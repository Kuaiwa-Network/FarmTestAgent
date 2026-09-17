# FarmQA Controller Queue Implementation Plan

> Execute inline with the executing-plans and test-driven-development skills.

**Goal:** Persist a single-controller FIFO reservation queue tied to authenticated Linear events.
**Architecture:** Add ControllerStore to the receiver SQLite ledger; hook the existing Stop transaction into it. Explicit operator enqueue only; no worker dispatch or game actions.
**Tech stack:** Python 3.11+ standard library and SQLite, Windows.
**Spec:** ../specs/2026-09-17-controller-queue.md

## Constraints

- Retain all existing session routes and event statuses.
- No gameplay, AI calls outside the existing bridge, or client/server edits.
- No secrets, reservation tokens, or prompt text in logs/reports/status.
- Never reclaim active ownership on timeout/restart.
- Work from commit 4175112 in the isolated controller worktree; no PR merge/push.

## Task 1: Queue and Stop integration

Files: tools/farmqa_controller.py, tools/linear_farmqa.py,
tests/test_farmqa_controller.py.

Interfaces: ControllerStore(db) uses the caller's SQLite transaction;
enqueue(event_key) returns the stable request ID; acquire(owner) returns an
active reservation including token or None; release(request_id, token) closes
that reservation; cancelled(request_id, token) reads owner cancellation;
stop(organization_id, session_id, cutoff_ms) operates inside the receiver's
authenticated Stop transaction. status() returns allowlisted metadata only.

- [x] Write failing regression cases using real temporary SQLite databases and
  the existing signed-event BridgeTests fixture. Assert FIFO, one winner from
  two independent connections, target immutability, Stop isolation/cutoff,
  crash persistence, wrong-token rejection, idempotent release/enqueue,
  late enqueue after Stop, and status redaction.
- [x] Run `python -m unittest discover -s tests -p test_farmqa_controller.py -v`
  and confirm the missing queue contract fails.
- [x] Implement the store, checked schema/index and enqueue/status CLI. Hook
  ControllerStore initialization and stop() into BridgeService. Keep the store
  transaction-neutral; standalone callers use BEGIN IMMEDIATE.
- [x] Run the focused tests, then all test_*.py tests. Fix concrete failures.
- [x] Exercise a private backup copy of the live ledger: migrate and compare
  every original event status and session mapping; use synthetic pinned jobs
  only in that copy for a two-process reservation/cancellation check.
- [x] Record redacted evidence, operator instructions, and limitations. Review
  the change, run diff checks, and commit locally. Integrate into the deployment
  checkout only by fast-forward, restart just the receiver, and verify identity,
  one listener, preserved mappings, and an empty live controller queue.
