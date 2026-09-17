# Supervised pointer cancellation — 2026-09-17

**PASS for a synthetic Stop driving the real Unity pointer fixture.** A separate
process could not acquire the occupied queue, a second gesture was rejected,
cancellation suppressed the pending click, and the next queued request clicked
successfully after the original task and input had finished. No gameplay worker
was deployed. This is not proof of exclusive control over arbitrary MCP/OS callers.

## Target and scope

Original client `D:/AgentWorkSpace/Farm/Farm-Client`, clean commit
`65feb61d4b9c6a7f79cee6efefdfea88140219dc`, Unity 2022.3.62f3,
StandaloneWindows64, instance `Farm-Client@6d4c4b2750085821`. The four loaded module
IDs matched the previous live-session run, including HotUpdate
`c21a2cb3-b894-4cbc-9dbb-6024685fc399`. No refresh, compile of client files, project
switch or Editor restart was needed. Complete build provenance remains a separate
limit; these are fresh identity comparisons, not a new controlled build.

Started in clean Edit Mode with no active Editor test and an empty production
controller queue. Entered Play Mode and observed LoginView, unauthenticated and
transport disconnected. Created a temporary opaque FairyGUI panel whose only
handlers append down/up/click counters. [Screenshot](evidence/fixture-visible.png)
shows that panel over the game area. No game buttons were used, no login occurred,
and no account-state operation was performed; saved progress was not inspected.

## Verification

The [replay scenario](../../tests/scenarios/farmqa-pointer-cancellation.md),
[C# fixture](../../tests/probes/pointer-cancellation.cs.txt) and
[opt-in harness](../../tests/probes/run_pointer_cancellation.py) are QA-owned. The
C# executes in memory; nothing was added to the client. The harness creates a new
private SQLite database with two synthetic sessions; actual BridgeService signature
validation and ControllerStore transitions run, while external delivery is mocked.

| Observation | Result |
|---|---|
| A owns reservation; separate inert-worker process tries to acquire | Blocked |
| First real pointer hold hits fixture target | Exactly one down; busy/active/held true |
| Second pointer request during hold | `pointer busy`, no additional down/click |
| Synthetic signed Stop for A | A cancel_requested; B queued; competing process still blocked |
| Owner sends CancelPointer | Still busy/active/held in that response; no early release |
| Later original-task observation | `cancelled by caller`; down/up, zero clicks; busy/active/held false; Stage touches zero |
| A released after that observation | cancelled; B then acquired |
| B's short fixture click | Success; cumulative down/up/down/up/click; quiescent |
| Cleanup | B released, panel disposed, zero captured Console errors since gesture start |
| Final Editor/source | Edit Mode, clean StartScene, identical source/index snapshots, production queue still empty |

The first quiescent observation was 28 ms after the cancellation-call observation,
17 game frames later. This is an observation interval on this run, not a guaranteed
cancellation latency or SLA. The complete harness process exited 0 in about 4.8 s.
The 132 existing Python tests also passed in 15.696 s; they remain synthetic and do
not by themselves prove the live pointer result.

[Verification summary](evidence/verification.json) and [trace](evidence/trace.json)
record the exact observations. Ownership tokens, account data, and raw game logs
are excluded. Private originals are under `.local/pointer-cancellation/` in the
main QA checkout. The initial probe compilation failed because `AsTask` is an
extension method outside the default namespace imports; using its fully qualified
static method fixed the probe. It then correctly rejected Edit Mode before any
fixture/input mutation. These were operator-probe checks, not client defects.

Review found no blocking issue. Clarified setup-before-acquire ordering and the
polling budget: 15 seconds schedules observations, while each in-flight HTTP call
has a separate 20-second timeout. Slow tool overhead can exhaust the eight-second
hold and cause a safe fixture failure. There is no automatic retry.

## Remaining limits and next step

The harness is supervised, uses synthetic Stop, and executes a fixed local test.
It is not connected to live Linear work. Queue ownership is cooperative; the driver
prevents overlapping simulated gestures, but neither fences arbitrary direct MCP
calls, the user's mouse, or a stale owner. CancelPointer is global to the simulated
pointer, not token-bound. A cancel cannot undo a server request already sent. Worker
crash, lost tool response, paused Editor, scene change and reconnect were not tested
here. Physical cancellation under those failures remains unverified.

Next implement a narrow controller adapter around these verified primitives:
validate the reservation and actual target before each permitted action, keep
identity and action in the same ownership scope, and retain the slot until that
exact action is observed quiescent. Verify stale-owner and lost-response behavior
on this harmless fixture before enabling any game action. Do not promote the
diagnostic to a gameplay permit or treat this report as automatic Codex interruption.
