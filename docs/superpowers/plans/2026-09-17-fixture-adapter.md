# Fixture controller adapter implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind the approved controller queue to the verified harmless pointer fixture, rejecting retired owners and reconciling lost responses without restarting an action.

**Architecture:** One action per reservation is persisted before dispatch. The Unity-side fixture retains action IDs and closed records for the life of the panel, so delayed start/cancel packets cannot affect a successor. Release requires fresh evidence that the exact action is closed and input is quiescent; unknown state keeps the slot held.

**Tech Stack:** Python 3.11+ standard library, SQLite, existing loopback Unity MCP, QA-owned in-memory C# fixture.

**Spec:** Approved single-controller design in `../specs/2026-09-17-controller-queue.md`, `../../farmqa-architecture.md`, and the next step approved after the supervised pointer-cancellation report.

## Constraints

- Only the existing temporary panel target at unauthenticated LoginView. No arbitrary path, code, gameplay, account operation, scene switch, OS pointer injection or deployment.
- Client checkout remains read-only; reuse the current isolated QA worktree.
- Keep ownership token in Python memory. Public action IDs identify operations, not credentials or protection against arbitrary MCP callers.
- No automatic takeover or pointer-start retry. Exact-action cancellation can be repeated until remotely acknowledged. Domain reload/fixture loss fails closed. Cancellation cannot undo a click or request already dispatched.
- Existing read-only identity diagnostics remain unable to issue gameplay permits.

## Task: One request-bound fixture action

Files: `tools/farmqa_controller.py` (action ledger/release interlock), new
`tools/farmqa_fixture_adapter.py` (owner and transport boundary), new
`tests/probes/fixture-adapter.cs.txt` (fixed Unity action protocol),
`tests/test_farmqa_fixture_adapter.py`, and opt-in live replay/evidence.

Interfaces: `FixtureAdapter(store, client).start(request_id, token, binding)`,
`.observe(request_id, token)`, `.finish(request_id, token)`. Binding pins instance,
project, commit, HotUpdate MVID, build target and existing fixture run ID. No target
selection or source checkout is performed. Client implements read-only validation
and a fixed `exchange(operation, action_id, binding)` protocol.

- [x] Add failing tests against real SQLite, synthetic authenticated queue events and a controlled remote test double.
- [x] Add the action ledger/release interlock and adapter. Guard terminal owners before any transport call; commit intent before remote mutation.
- [x] Add the Unity fixture protocol: start once, query status, cancel exact active action or fence not-yet-started action, close only after completion/quiescence. Keep closed records to reject late operations.
- [x] Run targeted tests and review failure behavior before live use.
- [x] Revalidate the actual Editor/source; set up the harmless panel and run normal Stop, lost-start-response, delayed-old-packet and successor checks. Leave Unity in Edit Mode afterward.
- [x] Run the Python suite, save redacted evidence and limitations, update memory.
- [x] Commit locally. No push/deployment in this increment.

Verification: `reports/2026-09-17-farmqa-fixture-adapter/report.md`; 145 tests pass,
including 13 adapter tests. Live A/B/C replay passes with wrapper-injected failures.
