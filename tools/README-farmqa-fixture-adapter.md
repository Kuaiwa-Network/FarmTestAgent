# FarmQA fixture adapter

`farmqa_fixture_adapter.py` connects the reservation library to one fixed pointer
test surface. It is opt-in Python library code, not a daemon, receiver mode,
gameplay permit, or general computer-use API. No deployment occurred in this
increment. See the [live report](../reports/2026-09-17-farmqa-fixture-adapter/report.md).

## Contract

`FixtureAdapter(store, FixtureClient())` takes a `ControllerStore` using an existing,
migrated SQLite connection. One synchronous caller owns that connection. Acquire a
reservation normally; keep its token private. Adapter calls must not be enclosed
in a caller transaction because network calls must never block Stop's write lock.

- `start(request_id, token, binding)` validates the active owner and pinned target,
  checks source/instance readiness, commits a unique action intent, then starts one
  fixed eight-second hold on `root:FarmQACancelFixture.target`. Repeated start for
  that reservation is rejected, including after a lost response.
- `observe(request_id, token)` queries the exact recorded action. If the reservation
  has Stop requested but remote cancellation is unconfirmed, it sends an idempotent
  cancel for that action ID. An attempted send is not an acknowledgement.
- `finish(request_id, token)` requires completed/quiescent observations, asks Unity
  to close the exact action, validates that response, persists closed state and
  releases the reservation. It returns the observation plus `reservation_state`.
  `cancelled` is queue state; inspect `success` and `events` for what actually ran.

The binding has exactly `instance`, `project` (absolute path), `commit_sha` (40 hex),
`hot_mvid` (UUID), `build_target` (`StandaloneWindows64`), and `run_id` (32 hex).
The reservation must pin the same project/commit and `offline-login-fixture` as its
synthetic environment. The panel must already exist and be visually inspected.
The adapter does not create it, enter Play Mode, log in, select an account, or use
OS input. All gestures use Unity MCP and GameTestDriver pointer simulation.

Each Unity operation checks stable Play Mode, actual project, build target,
HotUpdate MVID, unique loaded HotUpdate assembly, unauthenticated LoginView,
disconnected game transport, and the same fixture panel/run ID. This is a fixture
identity check, not complete build provenance or authenticated gameplay readiness.

## Failure and ownership rules

`controller_actions` records one action per reservation, its binding, attempted
cancellation and allowlisted observation. Intent is committed before dispatch.
`pending` and `uncertain` actions block `ControllerStore.release`, including an
ordinary cooperating caller attempting to release early. Only confirmed `closed`
state permits release. All participating code must use the updated release guard;
direct SQL writes or older library versions are outside this contract.

The Unity fixture retains records for up to 128 action IDs. Start is performed at
most once per ID. Cancellation before start creates a record that prevents a late
start. Closed records remain until panel disposal; old start/cancel packets return
the retired record without touching a newer owner. IDs are correlation values,
not secrets or authentication for an arbitrary MCP caller.

Lost response, malformed/stale/mismatched observation, missing fixture, domain
reload, paused/busy Editor or source/module mismatch must not be interpreted as
quiescence. Preserve the reservation and evidence. With the original token, a later
observation can reconcile a lost start/close response. There is no token recovery,
automatic takeover or force-unlock. A dead process does not prove its remote task
stopped. Polling drives cancellation; this library has no independent watchdog.

Pointer start is never retried. Exact-ID cancellation may be retried until a
validated acknowledgement; remote records make that safe for successors. A late
Stop cannot undo a click or service request already dispatched. The eight-second
hold/driver playback bound still needs advancing Unity frames for cleanup. MCP
HTTP calls retain their existing per-call 20-second timeout.

The fixture protocol and SQLite guard protect cooperating callers. They do not
fence unrestricted execute_code, other direct game tools, the user's mouse, or OS
input. No automatic Codex task interruption is added.

## Verification

```text
python -m unittest discover -s tests -p 'test_farmqa_fixture_adapter.py' -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

Unit tests use real SQLite and a controlled remote test double. The separate
[supervised scenario](../tests/scenarios/farmqa-fixture-adapter.md) exercises the
real Unity protocol using local transport-fault injection and replayed old packets.
No real network outage, live Linear Stop, process kill, or gameplay is claimed.
