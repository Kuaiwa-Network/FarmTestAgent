# Supervised fixture adapter and uncertain delivery

Read the [adapter contract](../../tools/README-farmqa-fixture-adapter.md) and
[pointer fixture scenario](farmqa-pointer-cancellation.md). Scope is the same
opaque counter-only panel at LoginView; no login or game action.

1. Establish one idle Editor, no active production controller request, matching
   clean source revision, expected HotUpdate MVID and Windows build target.
2. Save a private JSON binding with the six fields in the adapter contract. Generate
   a fresh run ID. Enter Play Mode and verify LoginView, unauthenticated/disconnected.
3. Execute `tests/probes/pointer-cancellation.cs.txt` with that run ID and operation
   `setup`, safety checks enabled. Inspect the panel screenshot before gestures.
4. Run the opt-in harness below with a NEW ignored output directory. It creates its
   own synthetic queue; do not point it at a production ledger. Keep assertions on.
5. Require each expected rejection and all three final outcomes; inspect the trace.
   Any unexpected failure keeps the reservation for investigation. Do not force
   release, resend the pointer start, or silently reuse the panel/run ID.
6. On success the harness disposes the panel. Stop Play Mode separately; leave the
   Editor open. Verify clean scene, unchanged source/index and idle production queue.

```text
python tests/probes/run_fixture_adapter.py --binding <private-binding.json> --output <new-private-directory>
```

| Request | Injected condition | Required result |
|---|---|---|
| A | Drop start response AFTER Unity dispatch; fail first cancel BEFORE dispatch; drop close response AFTER remote close | Retry start/early release/competing acquisition rejected; later exact-ID cancellation acknowledged; down/up with no click, completed/quiescent/closed; then cancelled reservation |
| B | While held, send retired A's start and cancel directly through fixture protocol | A's old records returned without changing B; B completes exactly down/up/click and releases |
| C | Fail start BEFORE dispatch; Stop and close; then deliver delayed start packet | Completed/closed cancellation with started false and no events; late start cannot activate |

Faults are deliberately injected in a local wrapper around the real MCP call.
This is not an actual network outage or live Linear test. The synthetic events are
authenticated through the real receiver code; outgoing delivery is mocked. Wrong
module identity is also rejected before any fixture press.

Observation loops have a 15-second scheduling budget; an in-flight HTTP request has
its own 20-second timeout. Tool overhead can exhaust the eight-second hold and make
the fixture fail safely. Never weaken the event/cancellation assertions to hide it.

Save source/Editor identity, meaningful observation transitions, injection points,
final queue state, screenshot and cleanup. Keep ownership tokens and raw game logs
out of evidence. This does not exercise OS touch/mouse injection, process death,
domain reload, paused-frame cleanup, real server effects or authenticated game
actions. A held queue prevents a successor; it is not proof a remote action stopped.
