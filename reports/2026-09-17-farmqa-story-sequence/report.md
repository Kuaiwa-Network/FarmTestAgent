# Supervised introductory story sequence — 2026-09-17

**Navigation PASS; zero-new-Console-error check FAIL.** Five background clicks
advanced story steps 10 → 20 → 30 → 40 → 50 → 60. One final button click reached
MainView with the expected guide dialogue, `小姐，我们先培植土豆吧。`, at guide
group 10/step 2 with checkpoint not reached. The final action also recorded the
known `[ShopService] QueryShop(13) failed: 2` error (ENV-003). No tutorial completion,
planting journey or clean end-to-end harness pass is claimed.

Compare [before](evidence/before.jpg) and [after](evidence/after.jpg), and the
[redacted verification](evidence/verification.json). The final dialogue was not clicked.

## Target and scope

PR #16 was confirmed merged at `8c564ef0bc26f60e55cfb0840152aa135d4ce682`.
Work continued on `codex/farmqa-story-sequence` in the isolated QA worktree.
Target: original `D:/AgentWorkSpace/Farm/Farm-Client`, clean client commit
`b8170a559909fccc21b488e47584f20e02a42104`, Unity 2022.3.62f3,
StandaloneWindows64, instance `Farm-Client@6d4c4b2750085821`.
HotUpdate MVID `74aa1b33-262f-4ebd-ace7-dd394e7eca20`.

Fresh preflight matched four loaded modules with disk DLL/PDB identities and
available source checksums (1,297 HotUpdate, 302 MCP Editor, 19 AOT, 15 Nova).
Each has one unavailable generated document. This is not complete build attestation.
No Editor restart, refresh, project switch, source edit or Spine setting change.

Reused the authorized dedicated account on 公共测试服, independently rechecked
selected account/server expectations, and issued one 50 ms login click. This
login returned to story step 10. The prior step 20 was an observed runtime state;
we did not reset the account or assume each dialogue step was persisted.

Live config showed fixed story steps 10/20/30/40/50/60, with final next step 0.
Source inspection of StoryPlayView, PlayStoryStepHandler, GuideService and
PlayDialogueStepHandler established the intended effects: Scripted mode closes
the story without its reward-claim branch, advancing guide step 1 to dialogue
step 2 before checkpoint step 3. Live GuideModel/config confirmed that sequence.
This is source reasoning about service effects, not network-level proof that no
server write occurred. No guide/GM/breeding/reward action was explicitly invoked.

## Implementation and review

The [sequence adapter](../../tools/README-farmqa-story-sequence.md) adds a strict
integer step binding to the existing authenticated request/action protocol.
The shared Unity probe retains the single-step adapter's default, and admits
only the six fixed story transitions in sequence mode. It checks session, actual
hit target, story/config and guide prerequisites before input/event bubbling.
The final positive result requires the exact guide dialogue, not merely MainView.

Review found a closure race: validating one observation then delegating to a
method that obtains another could release after input finished but before the
dialogue appeared. The new pending→complete-but-unavailable regression failed
on that implementation and passed after Python used one closure observation and
validated the returned close result. Unity also checks the resulting state before
releasing its owner. Late cancellation after a recorded click holds ownership;
it cannot prove rollback and may require manual recovery indefinitely.

Review also removed a proposed future-step negative from the live harness before
dispatch: stale caller state might make that supposedly invalid final click real.
Only the six ordered, guarded action starts ran. Unit helper mistakes were fixed
before verification; no game change was used to satisfy a test.

## Live observations and failure handling

Each nonfinal action used `ClickAt` at the freshly resolved hint centre, hitting
the captured background at approximately `(486.723, 32.885)` Unity screen pixels.
The final `Click("endBtn",50)` hit `GRoot..endBtn.icon` at approximately
`(484.022, 37.113)`. All six recorded down/up/click, successful completed input,
no guard loss and the expected resulting state. These are Unity GameTestDriver
pointer gestures; screenshots used Computer Use. OS touch/multitouch is untested.

| Transition | Result | New Console errors |
|---|---|---|
| 10 → 20 | advanced, closed/released normally | 0 |
| 20 → 30 | advanced, closed/released normally | 0 |
| 30 → 40 | advanced, closed/released normally | 0 |
| 40 → 50 | advanced, closed/released normally | 0 |
| 50 → 60 | advanced, closed/released normally | 0 |
| 60 → MainView + guide dialogue | finished; harness stopped at Console assertion | 1, ENV-003 |

The original harness exited at that Console assertion before closing the final
action. Its private ledger retains an active reservation because the ephemeral
owner token was lost on process exit. It was not reclaimed, reset or reused.
After inspecting the exact error and revalidating the pinned source/session,
the operator re-observed the same final action, confirmed finished/quiescent,
and sent its exact remote close without another click. Unity acknowledged closure.
This is supervised reconciliation, not a demonstrated automatic recovery path.

The harness now records observed outcomes and closes verified actions before
raising for new Console errors, preventing that avoidable hold. A mocked regression
verifies it closes and saves the first action, reports the error and does not start
another. The revised error path was not replayed live; no extra account reset or
story replay was performed to claim it passed.

## Verification and final state

Python suite: **187 tests passed** (10 new sequence/harness tests). The shared C#
probe compiled and executed live for all six steps. Review found no remaining
blocker for this supervised scope. The UI closure-race and late-cancellation
regressions are mocked, not claims of live async-race/Stop transport coverage.

Final live observation: MainView, one GuideDialoguePanel, guide group 10/step 2,
checkpoint false; six sequence records remotely closed, Unity owner null, no
held input or Stage touches. Account/route/generation and clean pinned source
still matched. Exited Play Mode to clean StartScene; no compilation/update/pause,
temporary login task/marker cleared, action tombstones retained.

All authored artifacts are in this QA repository. Client source remained clean.
Production receiver, tunnel, worker configuration and database were not modified.
The private failed synthetic ledger remains quarantined under `.local/story-sequence/`;
its final reservation is still active, despite confirmed remote closure. Private
account bindings, route hashes, player IDs and credentials are excluded from Git.

## Next step and limits

Next: inspect the first guide dialogue and breeding tutorial's exact UI/requests,
then implement one bounded supervised interaction toward the planting journey.
Re-observe progress on login; do not silently reset it or assume guide step 2 persists.

No autonomous gameplay worker, live Linear Stop during this sequence, actual
reconnect, process-crash recovery, network-outage recovery, arbitrary OS/MCP caller
fencing, Android execution or complete build provenance is verified. Stable hosting
and production deployment are unchanged. ENV-003 remains unresolved.
