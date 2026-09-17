# FarmQA read-only target identity — 2026-09-17

Outcome: **implemented and live-checked diagnostics; gameplay remains BLOCKED**.
PR #8 was confirmed merged at `665018d`. Work was isolated on
`codex/farmqa-identity`, preserving the deployment checkout and client changes.

## Implementation

The standalone [identity command](../../tools/README-farmqa-identity.md) reads an
existing queued/active controller request, inspects local Git and the selected
live Editor, and appends allowlisted diagnostics to the private database.
It leaves reservation state/ownership unchanged and rechecks the request after
external reads. There is no transaction spanning network calls, no imported
observation or cached-pass input, and no positive gameplay verdict in this version.

The standard-library transport talks only to the existing loopback MCP server.
It supports its observed JSON/SSE framing, pins one exact instance, reads current
state, and runs the existing fixed read-only readiness probe in memory. No game
methods, source edits, build, asset refresh, Play Mode or server login are used.

## Live evidence

The live CLI used a **synthetic signed-event fixture** copied into a private test
ledger, with its target commit set to the actual client SHA. The fixture's
`refs/heads/qa`, selection time `1`, and
`identity-inspection-no-server-selected` are fixture metadata, not an assertion
that such a branch/server was selected in production. No production Linear event
was retargeted, queued, consumed or delivered by this check.

- Unity: `Farm-Client@6d4c4b2750085821`, version `2022.3.62f3`, WindowsEditor,
  `StandaloneWindows64`, project `D:/AgentWorkSpace/Farm/Farm-Client`.
- Client SHA: `7dbf23bef80c660ceb5d384c2e99cff029e5b79a`.
- Current idle Edit Mode, project, commit and build target matched. The four
  expected loaded assembly names/module IDs were observed, including HotUpdate
  `58847d20-a524-43d9-b9da-3e2c9a1bc5ec`.
- Existing changes in four `tools/device-mcp` files caused a conservative dirty
  checkout mismatch. Their hashes, status, index metadata and commit were unchanged
  across inspection. The checker did not clean or alter them.
- Loaded-commit provenance and connected-server identity remain **unknown**.
  The limited source search found no provenance input in the inspected scripts
  and tools; it does not establish that none exists elsewhere. The current probe
  provides no authenticated game session reader, and Play Mode was off.
- CLI exit `2`, verdict `BLOCKED`, `execution_enabled: false`. One observation
  was persisted for the request, which remained `queued`.

See [live inspection](evidence/live-inspection.json) and
[client/reservation integrity](evidence/integrity.json). Module IDs distinguish
loaded modules; they do not prove disk equality or a reproducible build from Git.

## Verification and review

The new cases exercise real temporary Git repositories, real SQLite ledgers and
local HTTP fixtures. Only external Unity responses are simulated in unit tests.
They cover mismatched targets, unknown assemblies, stale/wrong/unsafe Editor
state, dirty-file and index changes, per-request snapshots, Stop during reads,
transport errors, JSON/SSE framing, redirects, and redaction. Live CLI verification
separately establishes compatibility with this installed Editor/MCP server.

Tests were written and observed failing before implementation. An index-only
change with an unchanged working file initially escaped the stability comparison;
the regression led to hashing Git index metadata as well. Independent review found
that an invalid final timestamp could persist an arbitrary object. Reproduction
failed before the fix; final timestamps now retain finite numbers only. Regression
coverage checks object/string/NaN/bool values and the actual saved SQLite JSON.
A Windows test cleanup connection leak was also corrected using explicit close.

All **121 tests passed**, including the previous 104 and 17 new identity/transport
tests. Command and exit status: [test evidence](evidence/tests.json).
The reviewer confirmed the timestamp fix and found no remaining actionable issues.
Unit/inert-process coverage is not live
gameplay or evidence of automatic Codex/Unity action interruption.

## Deployment, limitations and next steps

This increment is a locally committed standalone utility. No receiver restart,
scheduled worker, live-ledger migration, tunnel/firewall change or deployment was
performed. The utility initializes its diagnostic table only when explicitly
invoked against an existing ledger; no old receiver table is modified.

Instance/platform expectations are operator inputs saved with the observation;
the existing target schema does not pin them. Local Git snapshots omit ignored
files and cannot atomically attest an entire build or external dependencies.
The command samples state, so another task may change Unity between/after reads.
It does not enforce physical exclusivity, interrupt actions, or issue a reusable
permit. Malformed/unknown information never permits gameplay.

Next, agree on a trusted mapping from loaded artifacts to the selected commit
and a safe observation of the actual server/session. Those inputs must be
implemented/verified before adding a positive identity gate. Then implement and
verify exclusive action ownership, cancellation and quiescence before supervised
gameplay. Do not start by resetting the client, entering Play Mode, or guessing
an account/environment to eliminate these blockers.

The [architecture](../../docs/farmqa-architecture.md),
[topic memory](../../knowledge/linear-farmqa.md), and
[implementation plan](../../docs/superpowers/plans/2026-09-17-readonly-identity.md)
record the current state and scope.
