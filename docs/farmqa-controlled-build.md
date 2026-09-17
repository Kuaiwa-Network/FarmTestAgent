# Controlled Editor build and proposed session observation

Status: user approved the separate writable QA copy and controlled compilation
on 2026-09-17. The original client checkout remains read-only. This approval
covers imports, caches and compilation in the isolated copy with Play Mode off;
it does not authorize game source fixes, login or gameplay. Execution evidence
is recorded in the [execution report](../reports/2026-09-17-farmqa-controlled-build/report.md).
The import/compilation completed with Play Mode off and four loaded modules
matched the new outputs. Import changed two tracked files, so clean provenance
remains BLOCKED; this plan has not established a positive gameplay gate.

Later [import investigation and recovery](../reports/2026-09-17-farmqa-import-drift/report.md)
restored the pinned Spine settings in the isolated copy and verified two warm
reimports. That does not repair the historical manifest or verify assets imported
before recovery. A future claim of a clean baseline must account for actual asset/build inputs.
Later, the user accepted leaving Spine defaults unchanged and deferring the fix
for existing-content testing after the bounded asset comparison. The overwrite
is not by itself a blocker for subsequent read-only readiness work.

## Why a controlled build

The current loaded HotUpdate MVID matches the on-disk DLL, whose debug-directory
identity matches its portable PDB. All 1,293 checked-in source document checksums
match the current working files; Git blob comparisons differ only by LF/CRLF.
One compiler-generated document is not in Git. Compiler options, referenced
assemblies, generated inputs, asset/config identity and the other loaded modules
are not fully bound to that source commit by this observation. We should retain
this useful partial evidence without converting it into a complete identity pass.

## Concrete next action

Prepare a separate QA-only client checkout at
`D:/AgentWorkSpace/Farm/FarmTestAgent/.local/clients/farmqa-7dbf23b`, pinned to
`7dbf23bef80c660ceb5d384c2e99cff029e5b79a`, using Unity `2022.3.62f3` and build
target `StandaloneWindows64`. This uses the currently inspected revision, not
an invented default branch or a moving `main` reference. Reconfirm the target
before executing if a different build is requested.

1. Independently clone the local client repository without shared hardlinks or
   alternates. Do not add a worktree to the source client's `.git`, fetch into
   it, reset it, stash it, or copy its dirty working files or `Library` directory.
2. Resolve LFS pointers from existing local objects where available, verify each
   materialized object's hash, and report any missing objects before requiring
   downloads. The machine has Git LFS 3.7.1 and approximately 283.6 GiB free on D:
   at inspection; this is not a guarantee of final build size.
3. Record the selected commit, materialized source/input hashes, submodules and
   embedded packages, project/package settings, compiler version/options,
   generated sources where recoverable, and all referenced DLL hashes. Missing
   provenance is an explicit blocker, never a guessed value.
4. Close the current QA Editor normally, preserving any newly discovered unsaved
   state, and verify it has exited before directly launching the isolated project
   visibly with Play Mode off. Do not reuse EditorApplication.OpenProject: the
   observed switch crashed during shutdown. If MCP blocks normal exit, ask the
   user to close the window; do not disable its safeguards. Keep one QA Editor.
5. Let Unity import/compile inside that copy, with logs stored under private QA
   `.local/`. Do not fix compilation failures by editing game source. Record
   errors and any importer changes. No scene save, server login or gameplay.
6. After compilation is idle, capture source/input hashes again plus output DLL
   hashes, module IDs, PDB identities and compiler/generated-input evidence.
   Source drift, missing inputs or dirty tracked files prevent a complete record.
7. Load/read the resulting Editor module identities and compare them with the
   recorded outputs. Store the complete manifest privately with a content hash;
   publish only redacted evidence. Revalidation must compare actual live identity
   and current artifacts, not accept a historical observation as a permit.

This is an operational build record on this trusted QA machine, not a claim of
reproducible builds or an adversarial attestation/security boundary. It does not
authorize server changes, code fixes in the client, Android builds, or gameplay.
Do not automatically delete the isolated checkout or overwrite existing evidence.

## Session observation supported by inspected source

Source baseline is the same commit. These are candidate inputs, **not a newly
implemented or live-verified session reader**:

| Input | Existing source | Meaning / limitation |
|---|---|---|
| Auth generation | `Farm.Core.NetWork.Net.AuthSessionGeneration` | Changes as connections/session ownership change |
| Authentication | `Net.IsSessionAuthenticated` | Current generation equals the completed authenticated generation and is nonzero |
| Transport | `Net.IsTransportConnected` | Current network manager reports Connected; insufficient alone |
| Route | `Nova.NetManager._address` | Private last installed address; meaningful only with the current connected/authenticated generation; not a public environment-ID API |
| Player | `Farm.Core.Models.PlayerModel.PlayerID` | Written from authentication result; old values can survive reconnect failure |
| Account | `PlayerModel.AccountName` | Intended login identity; must not be treated as authenticated merely because it is populated |
| Zone | `PlayerModel.ZoneID` | Login currently writes literal `1`; **cannot identify the server environment** |

The live loaded Net type exposes the named public authentication/transport
properties. No property value, player model, token or connection address was read
in this investigation; the Editor was in Edit Mode.

The future safe snapshot must read only approved fields, establish one current
network manager/player model, and sample a stable generation before/after. It
must require both transport and authentication, compare the player identity with
the authorized test account, and compare the actual connected endpoint with an
explicit environment allowlist. A configured URL, server menu label, SDK name or
ZoneID is not that proof. A reconnect or generation change invalidates the sample.

Never serialize raw network/client objects, credential strategies, account dumps,
tokens, URI user-info/query strings or exception text. Parse/sanitize the route
inside the reader before returning metadata. Environment aliases/endpoints and
account expectations belong in private operator configuration. No environment or
account has yet been selected by this work.

Implement/verify the snapshot after the controlled build identifies the actual
loaded code. Positive session verification still needs a separately authorized
test login. Before any game-action worker, enforce physical ownership and verify
bounded cancellation/quiescence; neither this proposal nor a matching manifest
completes those gates.

Evidence: [provenance investigation](../reports/2026-09-17-farmqa-provenance/report.md).


## Session diagnostic implementation — 2026-09-17

The proposed reader now exists as a standalone QA probe/comparator; see
[usage and limits](../tools/README-farmqa-session-identity.md). It compares a
numeric player ID, avoiding account-name output, and a SHA-256 of the exact
credential-free connected route against private operator expectations. There is
no preconfigured environment or account. Live Edit Mode behavior is verified;
authenticated observation remains unverified. Neither matching fixture data nor
the new utility grants gameplay permission or modifies the reservation checker.


Subsequent user-authorized live verification on original client `65feb61d`
provisioned a dedicated public-test account and verified authenticated matching,
wrong-expectation rejection and post-Stop Edit Mode rejection. This supersedes
the initial reader's live-verification limitation, not the older controlled-build
provenance limits. See [live run](../reports/2026-09-17-farmqa-live-session/report.md).
