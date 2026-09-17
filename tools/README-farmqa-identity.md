# FarmQA read-only identity diagnostics

This command inspects the live Editor for an existing queued or active controller
request. It never starts gameplay or consumes/releases the reservation. It always
reports `BLOCKED`, because the current read-only probe cannot prove which commit
produced the loaded assemblies or which game server session is connected.

## Run

Use the QA checkout containing this utility and Python 3.11+. No extra Python
packages are required. The existing Unity MCP server must already be available
on loopback, with exactly one connected Editor. Discover its exact ID before
running; historical IDs and paths below are examples to revalidate.

```powershell
python tools/farmqa_identity.py --db 'D:/AgentWorkSpace/Farm/FarmTestAgent/.local/farmqa/events.sqlite3' --request '<existing-request-id>' --instance 'Farm-Client@6d4c4b2750085821' --build-target StandaloneWindows64
```

The database is explicit and must exist with a controller request previously
created by the authenticated event/enqueue path. The utility does not create a
ledger, select a default game branch, change a session's target or enqueue work.
For isolated infrastructure verification use a **synthetic** request in a private
fixture ledger, label it as such, and never use its reservation for real actions.

The default MCP endpoint is `http://127.0.0.1:9090/mcp`; `--endpoint` permits
another explicit port on `127.0.0.1`, only at `/mcp`. It does not accept credentials,
query strings, redirects, proxies or remote endpoints. It does not start/restart
Unity or MCP, install anything, refresh assets, compile client scripts, enter
Play Mode or invoke game-driver methods. The fixed existing readiness probe is
compiled in memory by MCP, with safety checks on.

Instance and build target are explicit operator expectations. They are stored
with each observation, not retroactively added to the older request snapshot.
The request supplies immutable repository, commit and intended server environment.

## Results and storage

Output is allowlisted JSON. Exit **2** means a persisted `BLOCKED` diagnostic;
exit **1** means no completed diagnostic was confirmed (for example invalid
request, Ctrl+C, or database failure). A transport/probe failure can be recorded
as BLOCKED with only its exception class, without raw error text. Never use exit
status alone as a QA result. No successful gameplay exit exists in this version.

Each invocation appends a new row to `controller_identity_observations` in the
selected database. The utility initializes only this diagnostic table, inside
a short transaction after collection. It rechecks target and request state under
that transaction; a Stop during collection becomes `request_current: mismatch`.
It never changes queue state or owner/token fields and holds no database lock
during external reads. A process failure can leave no observation, not a permit.

Checks use `match`, `mismatch`, `observed`, or `unknown`:

- Current idle Edit Mode is checked before and after the probe. Missing state,
  stale samples over ten seconds old, future timestamps, Play Mode, compilation,
  asset updates, tests or wrong instance block readiness. Unsafe initial state
  skips the probe. A dirty scene also blocks readiness.
- Project root, requested Windows/other build target, and full source commit are
  compared. Local Git is read only; no fetch, checkout or index refresh is used.
- Git status and SHA-256 hashes of modified/untracked files plus index metadata
  are compared before/after. All nonignored dirty files conservatively mismatch
  cleanliness, including tools/docs. Files over 16 MiB block hashing; symlinks,
  directories and paths outside the checkout are not read. Ignored assets/caches,
  source dependencies outside the checkout and atomic filesystem consistency are
  not established by these snapshots.
- Expected assembly names and loaded module IDs are recorded as `observed`.
  These do **not** establish disk/loaded equality or a build from the pinned SHA.
- Loaded source provenance and connected server environment stay `unknown`.
  The requested server name is never copied into an observed identity field.

Observations contain metadata, paths and hashes, never prompt bodies, credentials,
owner tokens, raw MCP replies, player dumps or file contents. Review allowlisted
output before copying it into a tracked report. The database remains private.

## Limits and next step

This utility is standalone, not wired to the inert worker, receiver or a scheduler.
It is neither a physical controller lock nor a security boundary against other
tasks on this machine. Its ten-second state freshness and twenty-second HTTP
socket timeouts are diagnostic settings, not an action-cancellation SLA. It only
supports the installed MCP server's JSON / single-line SSE reply framing. It
does not retry ambiguous operations. No gameplay action adapter exists.

Do not clean/reset the user's client to make a check pass. Establish an agreed
build provenance source and a safe live server/session identity reader before
allowing positive identity decisions. A future action worker must freshly check
these under exclusive ownership and verify cancellation before releasing.

Verification: `python -m unittest discover -s tests -p 'test_*.py' -v`.
Live diagnostic evidence and coverage limits are in the
[2026-09-17 report](../reports/2026-09-17-farmqa-identity/report.md).
