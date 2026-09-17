# Authenticated fixture admission — 2026-09-17

**PASS for the counter-only fixture.** Account, route and session-generation
checks now run in the Unity operation admitting a fixed pointer action. Wrong
identity prevented dispatch; Stop, uncertain delivery and delayed packets were
reconciled on the live panel. No real game control or production worker enabled.

## Target and state changes

PR #14 was confirmed merged at `324b16aacf81a8128b8ffd2745f1fc02f9ce533a`.
Work continued on `codex/farmqa-authenticated-fixture` in the isolated QA worktree;
the deployment checkout and receiver/tunnel were preserved.

Actual target: `D:/AgentWorkSpace/Farm/Farm-Client`, clean client
`b8170a559909fccc21b488e47584f20e02a42104`, Unity 2022.3.62f3,
StandaloneWindows64, instance `Farm-Client@6d4c4b2750085821`.
HotUpdate MVID `74aa1b33-262f-4ebd-ace7-dd394e7eca20`. Four loaded modules match
disk DLL/PDB identities; available source checksums match (1,297 HotUpdate,
302 MCP Editor, 19 AOT, 15 Nova). Each has one unavailable generated document;
this remains incomplete build attestation. No refresh, restart or project switch.

Reused the authorized dedicated account on 公共测试服. Refreshed the independent
player/route expectation through the selected server's login endpoint; credentials
stayed in memory. Entered Play Mode, verified the existing LoginView account/server
fields, then sent one successful 50 ms GameTestDriver `Click("btnStart")`.
The account reached StoryPlayView above MainView. No story advance, farm action,
GM mutation, reward grant or purchase was performed.

Created and later disposed the opaque runtime
[counter panel](evidence/panel-visible.jpg). All authored probe code is in the QA
repository; client files were unchanged. Computer use provided window activation
and screenshots. Gestures used Unity MCP/GameTestDriver pointer simulation,
not OS touch or multitouch.

## Implementation and verification

The [adapter](../../tools/README-farmqa-authenticated-fixture.md) requires an
existing immutable request/session binding, rechecks it and the pinned target
before durable action intent, and extends the fixture observation allowlist with
admission and session-loss states. The base adapter retains its offline scope.
Unity compares expected player/route/generation and original session object
references at admission. A fixture monitor and click handler check for loss.
Exact-ID observation/cancellation/closure remain available after a mismatch.

Eight new unit tests cover immutable binding, deletion during validation, invalid
generation/input, rejected admission, session-loss cancellation, inconsistent
observations, redaction, and uncertain/retired starts. The 161-test baseline passed;
the final full suite passed **169 tests in 17.538 seconds**.

Review found a cleanup replay defect: recreating a panel with the same run ID
forgot a cancelled action and accepted its delayed start. A live counter-panel
reproduction confirmed it; the replayed press was cancelled with down/up and no
click. The fix retains up to 128 used run IDs in the AppDomain without eviction,
rejecting reuse/exhaustion. The full fixed replay then passed:

| Case | Live result |
|---|---|
| Wrong player, route, generation at Unity admission | Unstarted, session-rejected, no events |
| Start response lost after dispatch | Second start rejected; original held press observed |
| Synthetic Stop for held A | Down/up, no click, cancelled and closed before release |
| Closed A start/cancel replay while B held | B completed one down/up/click, successful |
| C held; QA session predicate forced false | Session-loss cancellation, down/up, no click |
| D dispatch dropped, then Stop and late start | Tombstone remained closed/unstarted, no events |
| Cleanup then same-run setup | Intended run-reuse rejection |
| Fresh run, old-run start/cancel replay | Intended identity rejection; fresh action clicked once |

The C fault changed only the QA panel's predicate and restored it afterward.
It proves the monitor's cancellation path, **not real disconnect, session
replacement or reconnect behavior**. Stop events and transport faults were
injected locally using a private synthetic ledger; outgoing delivery was mocked.
No new live Linear Stop/delivery test was claimed. Final source review found no
remaining actionable issue.

## Evidence, final state and next step

[Verification JSON](evidence/verification.json) includes the redacted trace,
pre-fix reproduction, target/module observations, cleanup and private-file hashes.
Private binding/ledger and full local evidence stay under the main checkout's
`.local/authenticated-fixture/`; no account IDs, route hashes or credentials are
published. The known startup error `[ShopService] QueryShop(13) failed: 2` recurred;
it remains unresolved, so this is not a clean gameplay/Console pass.

Final observations: panel/root absent; no busy or held pointer and zero stage
touches; StoryPlayView/MainView unchanged before exiting; Unity open in clean
Edit Mode on StartScene; client source/index unchanged; production queue empty.
Temporary login task/Console marker cleared; used-run registry intentionally
retained. No receiver restart, production migration or deployment.

These are cooperative fixture guarantees. Arbitrary MCP/OS input, real process
death/network outage, domain reload, complete build provenance and frame-exact
cancellation of game handlers are unverified. A completed game effect cannot be
undone merely by cancelling input.

Next: define and implement one separately allowlisted, supervised navigation
action on the dedicated account, based on its actual current story/farm state.
Verify its target, expected state transition and Stop limitations before acting;
then work toward the first planting journey. Do not redirect the fixture's target
string to a game control or treat a diagnostic match as general permission.
