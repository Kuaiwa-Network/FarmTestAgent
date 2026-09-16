---
id: DRIVER-PTR-BLOCK-001
status: Editor-fixture-verified
last_verified: 2026-09-16
client_revision: 688da4652c9c2c3b5702c8e99d81e1480df419f7
---

# Covered input must not activate

Classification: driver interaction regression. This deliberately blocked gesture
passes the test only because it fails to activate the target. It does not exercise
a real farming modal or verify Android.

Existing fixture source:
`Assets/Scripts/HotUpdate/Tests/PlayMode/Driver/PointerSimulationTests.cs`.
No client test changes required. Start from idle Editor, no other controller/test.

Replay through Unity integration:

```json
{
  "mode": "PlayMode",
  "test_names": [
    "Farm.Tests.PlayMode.PointerSimulationTests.Click_RoutesPressReleaseAndClick",
    "Farm.Tests.PlayMode.PointerSimulationTests.CoveredTarget_FailsWithoutClickingEitherElement",
    "Farm.Tests.PlayMode.PointerSimulationTests.UntouchableTarget_FailsWithoutDirectFallback"
  ],
  "include_details": true,
  "include_failed_tests": true,
  "init_timeout": 120000
}
```

Await `get_test_job` with the returned job ID. The test fixture builds a temporary
FairyGUI root and resolves geometry itself. Its exact relevant calls/assertions are:

1. Positive control: `await GameTestDriver.Click("root:pointerTestRoot.target")`;
   expect success and event order `down, up, click`, then released pointer.
2. Covered case: put graph `blocker` over target, await a frame, call the same Click;
   expect `success=false`, `hitTarget` contains `blocker`, event list empty (neither
   target nor blocker activates). No fallback or second attempt.
3. Untouchable case: set fixture target `touchable=false`, call same Click; expect
   `success=false` and empty event list.

Observed result: 3/3 passed, job `eb4d1c3d27f5488fa67aef04e2526d88`.
Evidence: initial report `evidence/pointer-tests-request.json` and
`evidence/pointer-tests-result.json`. Per-gesture raw coordinates and screenshots
were not emitted by this fixture; do not invent them. The test source has explicit
assertions, not only a successful injection return.

Future farm-level extension (unverified): capture an underlying farm button's current
position, open a real modal through pointer input, then ClickAt that position. Observe
both modal behavior and unchanged underlying state/requests. Injection may succeed
while the underlying action correctly does not. Re-establish a positive control once
the modal is closed. Select the actual modal only during supervised learning.
