# Read-only session identity diagnostic

This standalone diagnostic observes an existing Unity game session and compares
it with private operator expectations. It does not enter Play Mode, log in,
change a reservation, enable a worker, or grant an execution permit. Every result
retains `verdict: BLOCKED` and `execution_enabled: false`, even when the sampled
session matches. The existing request-bound identity collector is unchanged.

Use the discovered exact instance ID and project root:

```powershell
python tools/farmqa_session_identity.py --instance <discovered-id> --project <project-root>
```

Without `--expected`, session matching stays unknown. Edit Mode returns
`observation_status: edit_mode` before reading any game statics or player/server
fields. Normal diagnostic exit is 2; input/CLI failures exit 1. Interpret the JSON,
not exit status as a gameplay result.

For a separately authorized existing authenticated test session, `--expected`
accepts a private JSON file with `player_id` (positive uint32 numeric ID) and
`route_sha256` (64 lowercase hex digits). There is no default account or server.
The route hash is SHA-256 of the exact UTF-8 WebSocket address string; there is
no canonicalization. Different casing, explicit ports or trailing slash produce
a mismatch even if the URLs might route equivalently. Derive the expected hash
from the operator-approved route, never by copying the observed hash just to
obtain a match. Keep expectations and observations in ignored `.local/` files.

The QA-owned C# probe:

- Returns early during import, compilation, paused/transitioning Play Mode or
  Edit Mode. It never invokes game commands or singleton-creating getters.
- Requires one loaded HotUpdate/Nova.Runtime assembly and one active Net,
  PlayerModel and NetManager object; current static owner references must match.
- Reads the current authentication generation and authenticated generation,
  manager connection state, transport generation/client identity, player ID and
  route. Re-reads ownership, generations, player ID, route and connection state
  before accepting the bounded sample. This is not a persistent session lease.
- Returns player/route identity only when authenticated, connected and stable.
  Rejects non-WebSocket routes and routes with user-info, query, fragment,
  whitespace or control characters. It returns only a route hash, never the raw
  URI, account name, credentials, full objects or exception text. A route hash
  is an identifier, not a secret or cryptographic server attestation.

The Python comparator requires explicit fields/types, a nonzero stable generation,
true authentication/transport/stability flags, and a sample at most ten seconds
old, never from the future. Valid wrong-player/route observations report mismatch;
missing, malformed, stale or disconnected observations stay unknown. The CLI
checks exact Editor/project and source stability around the probe, but does not
bind the result to a request, build manifest, approved account configuration or
physical controller ownership. Those remain separate gates.

The reflected private schema was reviewed against client `7dbf23b`; it is not a
stable public API. Unsupported fields/types produce an unavailable observation.
The probe compiled and its Edit Mode branch ran on the current original client
`a6dce07`; the initial report covered Edit Mode only. The later
[live run](../reports/2026-09-17-farmqa-live-session/report.md) verified one
authenticated match, wrong-player/route expectations and post-Stop rejection on
client `65feb61d`. Reconnect and all URI/schema failure branches remain unverified.
Python tests
cover comparison and selection/error handling using synthetic samples, not an
actual login, reconnect or transport. Source review is not runtime proof.

For reuse, the dedicated public-test account is recorded privately in the main
QA checkout at `.local/farmqa/test-accounts.json`, alias `farmqa-windows-public`.
Revalidate its live identity and actual progress on an agreed build each run.
Next verification: reconnect and session replacement under supervision. Do not enable gameplay through this utility. Complete physical
action ownership/cancellation separately.

[Execution evidence](../reports/2026-09-17-farmqa-session-identity/report.md).
