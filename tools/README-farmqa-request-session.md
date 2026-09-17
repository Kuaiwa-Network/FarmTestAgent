# Request-bound session diagnostic

`farmqa_request_session.RequestSessionInspector` connects the existing read-only
session probe to a currently owned controller request. It never logs in, dispatches
a gesture, acquires/releases ownership, or grants gameplay permission. A complete
match still returns `verdict: BLOCKED` and `execution_enabled: false`.

Use the library from the local controller caller with its in-memory ownership
token. Do not pass tokens on command lines or put them in reports. Both methods
reject an enclosing SQLite transaction; external reads must leave Stop writable.

```python
inspector = RequestSessionInspector(store)
inspector.bind(request_id, owner_token, private_expected)
result = inspector.inspect(request_id, owner_token)
```

`private_expected` has exactly these fields:

| Field | Independent expectation |
|---|---|
| `instance` | Exact discovered Unity instance ID |
| `build_target` | `StandaloneWindows64` in this increment |
| `hot_mvid` | Expected loaded HotUpdate module UUID, lowercase |
| `server_environment` | Exact environment selected in the request target |
| `player_id` | Operator-approved account's positive uint32 ID |
| `route_sha256` | SHA-256 of the exact WebSocket route from the selected server |

Derive account/route expectations independently of the observed session. The
dedicated account registry remains in the main QA checkout at
`.local/farmqa/test-accounts.json`, alias `farmqa-windows-public`. Revalidate the
server route on each authorized login; never copy a sample to manufacture a match.

`bind` requires an active owner, checks the environment against the pinned target,
and persists the target plus expectations once. An identical repeat is idempotent;
a different binding requires a new request. `inspect` rejects unbound, wrong-owner,
queued, stopped, released and changed-target requests before contacting Unity.

Inspection checks the exact instance/project, platform, HotUpdate MVID and Editor
state before and after the session probe, plus clean/stable source matching the
pinned commit. It checks session freshness after the remote work and after taking
the final database lock. Under that lock it rechecks active ownership, acquisition,
target and binding before appending evidence. A Stop during a matching sample
therefore records `session: match`, `request_current: mismatch`, and aggregate
`request_session_match: unknown`. The individual checks explain rejected results.

The additive `controller_session_bindings` and `controller_session_observations`
tables are created only by explicit library calls. Bindings contain private account
and route identifiers; keep the ledger ignored. Observation JSON contains check
results, timestamps, request/observation IDs and bounded status/error type fields.
It excludes account IDs, route hashes, tokens, raw objects and exception messages.
There is no production receiver migration or scheduled caller in this change.

## Replay

After an authorized supervisor has verified the target, logged into the dedicated
account and confirmed quiescent input, use a fresh private output directory:

```powershell
python tests/probes/run_request_session.py --project <client-root> --commit <full-sha> --expected <private-json> --output <new-private-directory> --mode authenticated
```

The harness creates synthetic signed bridge events and a separate SQLite ledger.
It checks correct identity, wrong player/route/module, Stop injected after the real
sample, and stopped-owner rejection. Outgoing delivery is mocked. It never logs in,
changes Play Mode, invokes game actions or touches the production queue. The
supervisor then exits Play Mode and repeats with `--mode edit-mode` and a second
new output directory. Unexpected failures retain the synthetic reservation for
inspection; do not mistake it for a live production owner.

## Limits and next step

This is evidence at observation time, **not a session lease or action permit**.
Independent reads cannot prevent a session, source or Stop change immediately
afterward. MVID/source checks do not prove full build provenance. The module does
not fence direct MCP/OS callers or prove physical input ownership; reconnect,
domain reload and actual process/network failure are not covered by this replay.

The subsequent [authenticated counter fixture](README-farmqa-authenticated-fixture.md)
implements the next step: account/route/session-generation checks inside the same Unity operation
that admits a single allowlisted action, with the fixture adapter's action-ID
fencing, cancellation and uncertain-delivery handling. Its bounded live replay passed on a
counter-only panel in an authenticated session; no game button is enabled.
The offline fixture scope and standalone diagnostic remain unchanged.

[Live verification](../reports/2026-09-17-farmqa-request-session/report.md).
