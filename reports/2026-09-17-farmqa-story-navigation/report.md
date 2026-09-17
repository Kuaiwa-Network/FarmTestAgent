# First supervised story navigation — 2026-09-17

**PASS: one real UI transition.** One pointer click advanced Scripted story 10
from step 10 to step 20. The new dialogue is visible in the
[after screenshot](evidence/after.jpg), compared with
[before](evidence/before.jpg), and matches the live story/config fields.
No tutorial completion or planting journey is claimed.

## Target and preparation

PR #15 was confirmed merged at `9f9b2f247686b264781e7b0ee9062156ec562ebc`.
Work continued on `codex/farmqa-story-navigation` in the isolated QA worktree.
The production checkout, receiver, tunnel and worker configuration were untouched.

Target: original `D:/AgentWorkSpace/Farm/Farm-Client`, clean
`b8170a559909fccc21b488e47584f20e02a42104`, Unity 2022.3.62f3,
StandaloneWindows64, instance `Farm-Client@6d4c4b2750085821`.
HotUpdate MVID `74aa1b33-262f-4ebd-ace7-dd394e7eca20`. Four loaded modules
matched disk DLL/PDB identities and available source checksums (1,297 HotUpdate,
302 MCP Editor, 19 AOT, 15 Nova). Each lacks one generated document; complete
build attestation remains unproven. No refresh, restart or project switch.

Reused the authorized dedicated account on 公共测试服. Independent player/route
expectations were refreshed from the selected login endpoint; credentials stayed
in memory. Entered Play Mode, verified existing account/server inputs and sent one
successful 50 ms `Click("btnStart")`. The account reached StoryPlayView above
MainView, Scripted story 10 at step 10. Live config showed narrative step 10 →
dialogue step 20 → step 30. Source inspection identified this nonfinal transition
as local story presentation; no finish/reward path was invoked.

## Implementation, review and live trace

The [narrow adapter](../../tools/README-farmqa-story-navigation.md) reuses immutable
request/session binding and durable action records. It admits only this story
transition, with session and UI checks both at admission and before event bubbling.
It distinguishes input completion from observed story advancement.

Review caught two defects before live dispatch: the original guard did not cover
the frame delay before pointer resolution, and the observation parser could accept
contradictory advancement evidence. Stage capture guards now reject changed
eligibility/hit targets before the story handler. Two failing regressions then
verified strict advancement and missing-field rejection. Initial unit-test helper
mistakes were corrected before the passing run.

The first live attempt targeted `continueHint` by path. The pointer driver rejected
it before any press: its centre actually hit `GRoot..bgLoader` at approximately
`(486.723, 32.885)` Unity screen pixels. The guard test therefore correctly failed
its expected rejection reason rather than reporting a pass. Story step remained 10,
the action closed, and input was quiet. This was a QA targeting mistake, not proof
of a product defect. One evidence-based correction derived the same current hint
centre and used `ClickAt` with a Stage guard requiring the captured background.
No direct-handler fallback, arbitrary coordinate parameter or game-source edit.

The corrected replay used a private synthetic ledger and mocked outgoing delivery:

| Case | Observed result |
|---|---|
| Wrong player, route, generation | Unstarted session rejection, zero events, step 10 |
| Start dropped before dispatch, synthetic Stop, late start | Closed cancellation tombstone, no press or advance |
| QA readiness predicate forced false after admission; monitor removed | Stage capture cancelled input, no accepted events, step 10 unchanged |
| Normal 50 ms background click, response lost after dispatch | Start retry rejected; original completed down/up/click, success, step 20 |
| Old cancelled request start/cancel replay | Closed old record returned; no extra action |
| New request after advancement | State-rejected, unstarted, step 20 preserved |

The predicate fault changed only QA guard state. It verifies the capture path,
not actual reconnect, account replacement or a real popup race. Stop was synthetic
and before dispatch; live Linear Stop during the short gesture was not retested.
The old long-hold cancellation fixture remains separate evidence.

The visible second line matches the next configured dialogue beginning
“小姐，这土豆本就是外邦稀罕物”. Story remains open, so no script completion,
tutorial advancement, reward claim, skip/end button, crop action or GM mutation
was tested. UI progress at step 20 is a runtime observation, not a claim that the
server persists that individual dialogue step across login.

## Validation and final state

Eight new tests cover binding/shape restrictions, unchanged state despite pointer
success, state rejection, uncertain delivery/Stop, redaction and inconsistent or
missing outcome data. Full suite: **177 tests passed**. The new C# probe compiled
in the live Editor and the corrected replay passed its assertions. Source review
and the live targeting correction are recorded separately from gameplay evidence.

The user briefly stopped Computer Use with Escape during the final screenshot;
work paused immediately and resumed on explicit instruction. The after screenshot
and state checks were then completed without another game action.

Final live checks: story 10/step 20, no popup or active advance, all action records
closed, no controller owner, no held input and zero Stage touches; source and
authenticated account/route/generation still matched. The known startup error
`[ShopService] QueryShop(13) failed: 2` recurred; the successful navigation action
recorded zero new Console errors. Unity was returned to clean Edit Mode on
StartScene. Source/index unchanged; production pending queue empty. Temporary login
task/marker cleared; action tombstones retained, event captures/monitors detached.

[Redacted evidence](evidence/verification.json) includes both live attempts,
target/module checks, pointer results, final state and private-file hashes.
Private account bindings, ledger and original evidence remain in the main checkout
under `.local/story-navigation/`. No credentials, player IDs or route hashes are
published. No deployment or production schema change occurred.

## Limits and next step

The adapter is deliberately limited to one nonfinal story transition. Direct
MCP/OS callers are outside its cooperative ownership boundary. Real process death,
network outage, domain reload, full build provenance and server-side rollback are
unverified. Stop cannot undo a handler already executed.

Next: continue the introductory story under a bounded, explicitly observed sequence,
checking final-step effects before allowing completion, then inspect the farm and
begin the first planting journey. Re-observe account progress on each login; do
not reset it or expand this adapter's target via a free-form string.
