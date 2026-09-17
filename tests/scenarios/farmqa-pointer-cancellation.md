# Supervised controller / pointer cancellation check

Infrastructure fixture; no gameplay journey and no production worker. The user
approved single-controller ownership/cancellation verification. Run on the one
identified Windows Editor, at LoginView, without logging in or changing game files.

## Preconditions

- Read CLAUDE.md, controller architecture, client pointer documentation and the
  previous live-session report. Revalidate source/module/instance identity.
- Production controller queue has no owner, Editor has no active test, and nobody
  else is driving it. The SQLite reservation does not fence arbitrary MCP callers.
- Start in clean Edit Mode. Enter Play Mode and establish LoginView, unauthenticated.
- Use a separate disposable SQLite fixture with synthetic signed events and mocked
  external delivery. Never insert test events into the production receiver.
- All pointer targets are on a temporary, opaque FairyGUI panel with only event
  counters; no game button, service call, login, GM action, or account reset.

## Actions and assertions

1. Execute `pointer-cancellation.cs.txt` with a unique `RUN_ID` and `OP=setup`.
   Verify the panel visually. It must cover LoginView without hiding/replacing it.
2. Queue A and B in different synthetic sessions; acquire A with its private token.
   A competing process must be blocked before any gesture starts.
3. `OP=start`: hold the fixture target for eight seconds, storing its asynchronous
   task in memory. Poll `status` until exactly one down event and held/busy/active.
4. `OP=compete`: attempt a second gesture only while the first is pending and busy.
   Require immediate rejection with `pointer busy`; no extra down/click event.
5. Submit an authenticated synthetic Stop to the fixture receiver. Require A
   `cancel_requested`, B queued, and another process still blocked.
6. The same owner checks `cancelled(A, token)` and sends `OP=cancel`. This is only a
   cancellation request. Do not release A based on this response alone.
7. Poll original task completion and input state (15-second scheduling budget;
   an in-flight MCP HTTP call has its own 20-second timeout). Require
   unsuccessful result `cancelled by caller`, down/up but zero clicks, busy false,
   simulation inactive, held false and Stage touch count zero. Unknown/error/
   timeout retains the reservation; never release in a generic finally block.
8. Release A only after those observations; require cancelled. Acquire B and use
   `OP=recovery` for one short fixture click. Require success, one additional
   down/up, exactly one click, and quiescent state. Then release B.
9. `OP=cleanup` only after task completion/quiescence. Stop Play Mode, leaving the
   Editor open. Verify source/index unchanged, scene clean, no fixture remaining,
   and no new Console errors. Record all failures honestly.

## Evidence and limits

After setup and visual inspection, the opt-in Python harness performs steps 2–8,
removes the panel and compares source snapshots. It never enters/exits Play Mode.
Pass the same generated 32-character lowercase hex run ID used for setup and a
new ignored output directory:

```text
python tests/probes/run_pointer_cancellation.py --instance <exact-instance> --project <absolute-client-path> --run-id <run-id> --output <new-private-directory>
```

Do not use Python's `-O` flag: this is an assertion-based test harness. Slow tool
compilation/RPCs or competing-worker startup can consume the eight-second hold
before Stop; that is a fixture FAIL, not permission to weaken the assertions or
retry a game action. If the harness fails, inspect the saved queue and original
gesture. Keep the reservation held until the remote state is understood. There
is no token recovery, force-unlock, or automatic retry path.

Save allowlisted before/after identity, event counts, gesture results, queue states,
times, screenshot and final source comparison. No tokens, raw login fields, or game
logs. `RUN_ID` identifies the temporary panel; it is not a security credential.

This checks the real Unity driver with an operator-controlled bridge-to-cancel
sequence. It does not test live Linear Stop, an autonomous adapter, stale-owner
fencing, crash recovery, OS mouse control, reconnect, or effects already dispatched
to the server. Queue ownership and driver busy rejection are distinct guarantees.
