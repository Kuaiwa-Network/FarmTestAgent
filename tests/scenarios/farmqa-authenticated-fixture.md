# Authenticated fixture admission and replay

Status: observed PASS on 2026-09-17, Windows Unity 2022.3.62f3,
StandaloneWindows64, client `b8170a559909fccc21b488e47584f20e02a42104`.
This is an infrastructure regression, not gameplay coverage.

Follow the [operator guide](../../tools/README-farmqa-authenticated-fixture.md).
Prerequisites: one quiet Editor/controller, clean pinned client, matching loaded
module, independent dedicated-account/server expectation, authenticated stable
session, fresh private run ID/output directory. Preserve account progress.

| Starting condition / action | Required observation |
|---|---|
| Panel ready; start with wrong player, route, then generation | Each session-rejected, unstarted, no events, terminal and quiet |
| A dispatched but its response lost | Durable uncertain intent; second start rejected; original down observed |
| Synthetic Stop for held A | Down/up, no click, unsuccessful; closure before reservation cancellation |
| B held; replay closed A start/cancel | Old closed records only; B completes exactly one down/up/click |
| C held; inject false QA session predicate | Session-lost cancellation, down/up without click; restore predicate |
| D start lost before dispatch; Stop then late start | Cancel-before-start tombstone; delayed start remains closed/unstarted |
| Cleanup; attempt same run ID again | Exact run-reuse/capacity rejection |
| Fresh run started; replay old-run start/cancel | Exact run-identity rejection; fresh action completes exactly one click |
| Cleanup and exit Play Mode | No panel, no held/busy pointer/touches; clean scene/source; Edit Mode |

Every result must satisfy its specific reason; a generic error or timeout is not
a pass. On unexpected outcome retain ownership and inspect the exact outstanding
task; do not retry a start or dispatch a game action as recovery.

The live predicate injection covers the fixture monitor path only, not a real
account switch, transport replacement or reconnect. Stop is locally injected,
not a new live Linear transport test. No actual game button is admitted.

[Dated report](../../reports/2026-09-17-farmqa-authenticated-fixture/report.md)
