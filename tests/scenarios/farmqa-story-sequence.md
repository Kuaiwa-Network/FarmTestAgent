# Introductory story to the first farm dialogue

2026-09-17: navigation PASS, zero-new-Console-error check FAIL (existing ENV-003).
Windows Unity 2022.3.62f3 / StandaloneWindows64, client
`b8170a559909fccc21b488e47584f20e02a42104`. No complete tutorial or crop journey.

Follow the [operator guide](../../tools/README-farmqa-story-sequence.md). Reuse the
authorized dedicated account on 公共测试服, with fresh source/module/session/UI
observations and exclusive quiet controller ownership. Start only at Scripted
story 10/step 10, guide group 10/step 1, checkpoint 3 not reached.

| Action | Expected observation |
|---|---|
| Five separate 50 ms background clicks, resolving each current hint centre | Exact story steps 20, 30, 40, 50, 60; same guide step and session |
| One 50 ms `Click("endBtn")` | Story view gone, MainView and one GuideDialoguePanel, expected potato dialogue, guide step 2, checkpoint false |
| Close each verified action | Completed, quiet, successful down/up/click, confirmed transition and remote closure before reservation release |
| Inspect errors and stop | Keep navigation and Console verdicts separate; no extra click to hide a failure |
| Save final screenshot/state, exit Play Mode | No live owner/held input, source unchanged, clean Edit Mode |

Malformed/unsupported steps and inconsistent outcomes are unit-tested. The
pending-input → completed-input-but-dialogue-unavailable race must retain ownership.
Late cancellation after a recorded click also holds for manual recovery. These
regressions are mocked; live cancellation during this short sequence is unverified.

Do not attempt a future-step click as a negative test: stale caller state could
make it a real final button press. Do not dismiss the guide dialogue, skip,
breed, reset progress, claim rewards or use direct handlers to obtain a pass.
Re-observe on every new login; intermediate dialogue progress is not proven persistent.

[Dated evidence](../../reports/2026-09-17-farmqa-story-sequence/report.md)
