# Authenticated counter fixture

`AuthenticatedFixtureAdapter` admits only a fixed eight-second pointer click on
the temporary `FarmQAAuthenticatedFixture.target` counter panel. It is an opt-in
library and supervised replay, not a deployed worker or a game-control API.

The caller first obtains controller ownership and binds independent account,
server-route and module expectations with `RequestSessionInspector.bind`. The
adapter requires that immutable binding and the same pinned target, checking both
again under the database lock before recording action intent. A prior diagnostic
match is never an action permit.

Its private binding contains exactly `instance`, `project`, `commit_sha`,
`hot_mvid`, `build_target`, `run_id`, `server_environment`, `player_id`,
`route_sha256`, and `generation`. Revalidate account/route independently against
the authorized account registry and selected server; sample the current session
generation only after that match. Use a new random 32-character lowercase hex run
ID. Keep bindings, owner tokens and the SQLite ledger outside Git and logs.

The rendered Unity probe checks the project, loaded module, platform and stable
Play Mode. Immediately before starting the fixed click, in that same Unity call,
it compares authenticated/connected state, player, route, generation and the
original manager/player/transport references. Mismatches produce a terminal,
unstarted record. An update monitor cancels a pending fixture click when its
session predicate fails; the panel's click handler also checks the predicate.
These are fixture-specific protections, not a general guarantee for game handlers.

Durable intent, no start retry after uncertainty, exact-ID cancellation, pointer
quiescence and acknowledged closure follow the existing fixture adapter. Status,
cancel and close remain usable after session mismatch. Closed records cannot
cancel the next action. Cleanup retains a used-run registry for this AppDomain:
at most 128 IDs, no eviction; reuse or exhaustion fails closed. A panel similarly
holds at most 128 action records. This registry is not persistent across domain
reload or process restart; do not reuse historical IDs or resume across those
boundaries without a separate recovery design.

## Supervised replay

Verify one quiet Editor/controller and the authorized dedicated account on
公共测试服 first. This harness does not log in or change Play Mode. Use a new
private output directory and a freshly prepared private binding:

```powershell
python tests/probes/run_authenticated_fixture.py --binding <private-json> --output <new-private-directory>
```

The harness creates its own SQLite database, synthetic signed events and mocked
outgoing delivery. It tests wrong account/route/generation, lost start response,
Stop, late packets, cancellation before dispatch, cleanup/run reuse, and a fresh
successor. Its session-loss fault replaces only the QA panel's predicate with
`false`, then restores it; it does not disconnect or replace the game session.
Unexpected failure retains the fixture/reservation for investigation. Reconcile
the exact action and verify released input before cleanup or another run.

The panel is opaque and counter-only. Input uses Unity MCP and GameTestDriver's
pointer simulation, not OS touch/multitouch. Production receiver, tunnel, queue
schema and Linear delivery are untouched. Direct MCP/OS callers are outside this
cooperative boundary. Real reconnect, process death/network outage, domain reload,
frame-exact cancellation and complete build attestation remain unverified.

[Scenario](../tests/scenarios/farmqa-authenticated-fixture.md) ·
[Live evidence](../reports/2026-09-17-farmqa-authenticated-fixture/report.md)
