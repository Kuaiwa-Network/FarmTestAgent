# Supervised story navigation

`StoryNavigationAdapter` is an opt-in library for exactly one action: advance
Scripted story 10 from step 10 to step 20. It reuses the controller's durable
intent, immutable request/session binding, no-start-retry rule, Stop propagation
and acknowledged closure. It is not connected to the production worker.

Use the same private binding fields as the
[authenticated fixture](README-farmqa-authenticated-fixture.md). Bind independent
account/route expectations with `RequestSessionInspector.bind` under current
ownership. Supply no path, coordinates, story IDs or arbitrary code. One action
is allowed per reservation and per fresh run ID. A bounded AppDomain registry
retains 128 run/action records without eviction; reuse with a different action
fails closed. This is not persistent recovery across domain reload or restart.

The Unity operation requires the pinned project/module/platform, stable Play
Mode, expected player/route/generation, Scripted story 10 at step 10, no popup or
active advance, an opaque story pane, and the expected nonfinal config links
10 → 20 → 30. It captures the actual view, pane, background and hint objects.
The pointer point is freshly derived from the hint's centre, converted to Unity
screen coordinates. `ClickAt(..., 50)` uses physical game input routing; Stage
captures permit only the captured background target. The hint itself is not
hit-testable at its centre on the verified build.

An Editor update monitor checks identity and eligibility while input is pending.
Stage captures recheck before normal down/up/click bubbling, preventing a changed
session, view, popup, step or hit target from reaching the story handler.
After an accepted click, step 20 is permitted for result observation. Exact-ID
status, cancel and close remain available after a state mismatch. Closure removes
the monitor/captures and retains a tombstone. `guard_lost` covers session or UI
guard loss; it is not a claim of a real transport disconnect.

`outcome: advanced` requires accepted/started input, completed successful pointer
execution, exactly down/up/click, observed step 20 and a matching captured session
and view. Pointer success with unchanged or unknown story state cannot pass.
Closed observations preserve their original result rather than reporting the
state of a later action. Unknown or inconsistent fields hold the action uncertain.

## Replay

After authorized login and fresh source/module/session/UI checks, with no other
controller or input activity and the account still at step 10:

```powershell
python tests/probes/run_story_navigation.py --binding <private-json> --output <new-private-directory>
```

The harness creates a private synthetic ledger and mocks outgoing Linear delivery.
It rejects wrong player/route/generation, cancels a start dropped before dispatch,
and verifies its delayed packet stays cancelled. A test-only false predicate is
installed after admission and the update monitor removed, proving the Stage
capture itself prevents normal event bubbling. This changes only QA guard state,
not the game session. A final normal action loses its response after dispatch;
the original is observed rather than retried, and must advance exactly once.
A new attempt from step 20 must be rejected. The replay is intentionally
inapplicable after advancing; do not reset account/game state to make it pass.

On unexpected failure, inspect the exact action and retain unresolved ownership;
do not retry start. A later Stop cannot undo a handler that already ran. This
replay covers synthetic Stop before dispatch and an injected event-guard failure,
not live Linear Stop during a 50 ms gesture, actual reconnect, process death,
network outage, arbitrary OS/MCP callers or complete build provenance.

[Scenario](../tests/scenarios/farmqa-story-navigation.md) ·
[Evidence](../reports/2026-09-17-farmqa-story-navigation/report.md)
