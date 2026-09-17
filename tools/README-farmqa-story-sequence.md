# Supervised introductory story sequence

`StorySequenceAdapter` admits six fixed transitions in Scripted story 10:
10 → 20 → 30 → 40 → 50 → 60 → the first guide dialogue above MainView.
It is opt-in and not deployed to the Linear worker. The existing
[single-step adapter](README-farmqa-story-navigation.md) keeps its original default.

Use the authenticated private binding plus integer `story_step`, one of
10/20/30/40/50/60. Each action needs a new reservation/run ID and an independent
request/session binding. There is no arbitrary path, coordinate or story parameter.
The shared probe checks exact source/module/platform, player/route/generation,
captured UI objects, fixed step/config links and guide group 10, step 1. Before
input it also requires the expected next guide dialogue and checkpoint 3 not reached.

The first five actions derive the current hint centre and use `ClickAt(...,50)`.
The last uses `Click("endBtn",50)`. Stage captures check eligibility and actual
hit target before down/up/click bubbling. After the click, the monitor permits
the intended UI transition but still checks the captured session. These are
GameTestDriver pointer gestures, not OS touches or multitouch coverage.

Finishing requires exact down/up/click, successful completed input, no guard loss,
the matching session, MainView, guide group 10/step 2, checkpoint false, and exactly
one GuideDialoguePanel displaying `小姐，我们先培植土豆吧。`. Input completion alone
cannot release ownership. Python checks the observation used for closure and its
returned result; Unity checks the transition again before detaching/releasing.
Closed records latch their result and retain the existing no-reuse tombstones.

## Supervised replay

Re-observe the designated 公共测试服 account after login. Do not reset its progress.
Verify source/module/session/config, screenshot, quiet input, no other controller
or test, actual Scripted story 10/step 10, and no popup before running:

```powershell
python tests/probes/run_story_sequence.py --binding <private-json> --output <new-private-directory>
```

The harness uses a new synthetic ledger and mocked Linear delivery. It admits at
most six clicks in 15 minutes, waits up to 15 seconds per resulting state, and
never retries start or sends a recovery click. Every step revalidates its target.
It stops at the first unexpected condition. A confirmed, quiescent action is
recorded and closed before reporting any new Console errors; such errors still
fail the run and prevent the next click. Do not dismiss the final guide dialogue.

If a call is uncertain, inspect its exact persisted action and actual Unity state.
Do not reuse an abandoned ledger or clear ownership merely because its caller
exited. The ephemeral reservation token is lost on process exit; automatic reclaim
and crash recovery are not implemented. A late cancellation after a dispatched
click can leave pointer success false even after the UI changes. This deliberately
retains ownership and needs manual recovery; observing a later screen alone does
not restore a successful result. Stop cannot undo a handler that already ran.

On this build, source inspection indicates story completion moves guide step 1
to dialogue step 2, before checkpoint 3. No scripted-story reward path was found.
This is source reasoning, not a server-side proof of no writes. No guide click,
breeding, planting, reward, skip or GM action is admitted by this increment.

[Scenario](../tests/scenarios/farmqa-story-sequence.md) ·
[Run evidence and limitations](../reports/2026-09-17-farmqa-story-sequence/report.md)
