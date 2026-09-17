# One scripted story advance

Observed PASS: 2026-09-17, Windows Unity 2022.3.62f3 / StandaloneWindows64,
client `b8170a559909fccc21b488e47584f20e02a42104`. This is one UI navigation
transition, not a completed tutorial or planting journey.

Prerequisites: [operator guide](../../tools/README-farmqa-story-navigation.md),
one quiet controller, independently identified dedicated account on 公共测试服,
clean pinned source/module, authenticated stable session, Scripted story 10,
step 10, no popup, no ongoing advance. Fresh private binding/run/output IDs.

| Step | Required evidence |
|---|---|
| Observe current story and configuration | Step 10 narrative, next 20 dialogue, subsequent 30; screenshot and UI/model fields agree |
| Attempt wrong player, route, generation | Each session-rejected, unstarted, no events, story unchanged |
| Drop start before dispatch; inject synthetic Stop; replay delayed start | Closed cancellation tombstone, no press or advance |
| Start with injected false QA readiness predicate and no update monitor | Stage capture cancels before normal bubbling; zero accepted events, step 10 unchanged |
| Start one normal background click; lose its response | Never retry start; observe original down/up/click, success, step 20 and new dialogue |
| Replay closed Stop packets; attempt a fresh action from step 20 | No extra advance; new action state-rejected and closable |
| Finish and exit Play Mode | All records closed, no owner/input, source unchanged, clean Edit Mode |

Resolve the hint centre from current geometry; input must hit the captured story
background. A wrong hit or changed UI/session is a rejection, never a reason to
invoke the handler directly. Do not use skip/end, reset progress, claim rewards
or repeat the now-inapplicable action. Timeout or ambiguous observation cannot pass.

The capture test injects a predicate fault rather than a real account switch or
popup race. Late Stop cannot roll back an already executed handler. OS touch,
multitouch and live Linear Stop transport are outside this replay.

[Dated evidence](../../reports/2026-09-17-farmqa-story-navigation/report.md)
