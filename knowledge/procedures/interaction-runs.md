# Interaction run procedure

P01 — status **user-confirmed**; prerequisites: authorized test target and account;
scope: Editor and Android; last verification 2026-09-16; evidence: initial user task.

1. Create a dated run folder with target/build manifest, controller ownership, account
   alias/verified session identity, baseline resources, and action/time bounds.
2. Mark the console before setup/actions. Capture screenshot, active views and current
   UI tree. Store separate logs for pre-existing errors, warnings and new errors.
3. Confirm state schema actually contains the fields used by assertions. Missing is
   unknown, not zero. Label optimistic snapshots; obtain authoritative evidence separately.
4. Resolve one target from fresh geometry. Save exact path or coordinates and resolution
   evidence in this run only. Await the gesture. Do not overlap gesture tasks.
5. Poll an explicit condition to a deadline; record both injection and outcome results.
   After scene/view/popups/scroll changes, capture again before the next action.
6. At a block, capture evidence and classify; one reasoned recovery at most. Unknown
   result is INCONCLUSIVE; missing prerequisite is BLOCKED; failed known expectation
   is FAIL. A negative test passes only if intended rejection/no-action is proven.
7. Save artifacts, update knowledge/issues/lessons, and replay successful procedures.

P02 — status **inferred**; source `docs/pointer-simulation.md`; same client source as
initial inspection; Editor only; reviewed 2026-09-16. Synchronous execute_code needs
a retained Task for async gestures. Use `.AsTask()` once, poll completion in subsequent
calls, and read a completed result only. Do not block Unity main thread with `.Wait()`
or an unfinished `.Result`. No custom task bridge was implemented in this workspace;
the initial fixture run uses the existing UnityTest/UniTask execution context.

P03 — status **observed** for fixture execution only; evidence `pointer-tests-result.json`;
Editor 2022.3.62f3/client 688da4652; verified 2026-09-16. Existing Unity integration can
run named interaction fixtures and return per-test assertions. This offers a replayable
infrastructure regression route without adding client code. It is not a gameplay runner.

Trace schema (one JSON object per line): `id`, `phase`, `starting_state`, `target`,
`command`, `arguments`, `expected`, `actual`, `status`, `evidence`. Add timestamps,
gesture start/end, timeout and screenshot/tree paths for actual gameplay steps.
Fixture timestamps come from the test job; do not invent unreported pointer positions.
