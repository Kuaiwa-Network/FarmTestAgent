# Fixture controller adapter — 2026-09-17

**Implemented and verified on the real Unity pointer fixture.** The adapter records
an action before dispatch, rejects retired/wrong owners, reconciles uncertain
delivery and prevents early queue release. Unity retains closed action IDs so old
start/cancel packets cannot affect a successor. This is a fixture-only library;
no production worker or gameplay execution was enabled.

## Target and method

Original client `D:/AgentWorkSpace/Farm/Farm-Client`, clean commit
`65feb61d4b9c6a7f79cee6efefdfea88140219dc`, Unity 2022.3.62f3,
StandaloneWindows64, instance `Farm-Client@6d4c4b2750085821`; HotUpdate MVID
`c21a2cb3-b894-4cbc-9dbb-6024685fc399`. Preflight recorded the four loaded module
IDs, source/index and Editor state. The adapter checks project/build/HotUpdate/run
identity inside each operation, with source/instance validation before start.
These checks do not constitute complete build-provenance attestation.

The Editor started in clean Edit Mode, with no running Editor test or production
queue owner. Entered Play Mode and verified unauthenticated/disconnected LoginView.
The same temporary opaque FairyGUI panel handled only event counters. No login,
account-state operation, game button, client edit, project switch or Editor restart.
Computer use only activated the window and captured the
[fixture screenshot](evidence/fixture-visible.png); gestures used Unity MCP and
GameTestDriver pointer simulation.

The [opt-in replay](../../tests/probes/run_fixture_adapter.py) used a new private
SQLite database, real BridgeService/ControllerStore code and synthetic signed Stop
events. Outgoing delivery was mocked. Faults were injected locally before dispatch
or after an actual MCP response; this did not interrupt the machine's network or
send live Linear traffic. Old packets were deliberately replayed through the fixed
Unity protocol below the adapter's Python ownership check.

## Results

| Check | Observed result |
|---|---|
| Wrong HotUpdate MVID | Rejected before input |
| A: lost start reply | Action remained recorded; retry start, early release and competing process acquisition rejected |
| A: first cancellation failed before dispatch | Later observation resent exact-ID cancellation and received acknowledgement |
| A: lost close reply | Reservation remained held until the next matching closed observation |
| A final | started true; success false; down/up, no click; completed/quiescent/closed; reservation cancelled |
| Retired A while B held | Python ownership check rejected A; direct old start/cancel returned A's closed record without cancelling B |
| B final | success true; exactly down/up/click; completed/quiescent/closed; reservation released |
| C: start never dispatched, then Stop | Remote cancellation record fenced the pending start; closed without a gesture |
| Delayed C start after release | remained started false/closed, no events |
| Cleanup | panel disposed; all remote action records reported zero captured errors; source/index unchanged |

Afterward Unity remained open in Edit Mode on clean StartScene. Production queue
was still empty and did not contain the new adapter schema; the receiver was not
restarted or upgraded. The private test ledger ended A cancelled, B released,
C cancelled. No automatic Codex task interruption was introduced.

[Verification summary](evidence/verification.json) and
[observation transitions](evidence/trace.json) contain allowlisted evidence.
Identical repeated status samples are omitted from the published trace; the full
private trace and its SHA-256 are retained under `.local/fixture-adapter/` in the
main QA checkout. No ownership tokens, credential fields or raw game logs are
published.

## Implementation checks and remaining limits

Added regression tests first, observed failure before implementation, then passed
the adapter cases. Review found that recording an attempted cancellation before
transport could lose Stop if dispatch failed. A failing before-dispatch test
reproduced it; cancellation now repeats until a validated remote acknowledgement.
Pointer start still never repeats. A strict-schema regression also rejects boolean
`true` as schema version 1. These were adapter implementation defects fixed here,
not client/game defects. The strict integer-schema check was added after the live
replay and unit-tested; the Unity protocol was unchanged, and the recorded final
observations also satisfy the stricter validator. The final Python suite passed **145 tests**, including
13 new adapter tests; external transport in those tests is controlled, not live.

The live check does not cover actual network outage, process death, domain reload,
paused Editor, authenticated game actions or server effects. Unknown state retains
ownership, but process death alone does not stop a remote gesture. The caller must
poll to propagate Stop; no independent watchdog exists. Queued/retired states and
Unity's closed records protect cooperating callers, not unrestricted execute_code,
direct game tools, old release-library versions, or OS input. Cancellation cannot
undo effects already emitted. The Unity fixture stores at most 128 action records
per panel and has no automatic recovery/reclaim path.

Next: bind the verified authenticated account/server observation to permitted game
actions under this ownership scope, keeping lost-owner recovery explicit. Continue
with a bounded supervised game-action increment only after those checks; do not
convert the current diagnostic or fixture binding into a general gameplay permit.
