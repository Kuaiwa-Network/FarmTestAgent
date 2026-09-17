# FarmQA provenance and session-source investigation — 2026-09-17

Outcome: **partial provenance established; complete build/session identity still
BLOCKED**. PR #9 was confirmed merged at `30909a1`. This investigation used a new
QA worktree on `codex/farmqa-provenance`; production bridge code/configuration and
the existing client checkout were left unchanged.

## Observations

Client: `D:/AgentWorkSpace/Farm/Farm-Client`, commit
`7dbf23bef80c660ceb5d384c2e99cff029e5b79a`. Live Editor:
`Farm-Client@6d4c4b2750085821`, Unity `2022.3.62f3`, WindowsEditor, idle Edit Mode.
The loaded HotUpdate MVID remains `58847d20-a524-43d9-b9da-3e2c9a1bc5ec`.

The existing DLL and portable PDB can provide more than filenames/timestamps:

- DLL MVID matches the live loaded MVID. The DLL's CodeView GUID/stamp match the
  portable PDB's content ID. These are metadata correspondence checks, not proof
  against malicious replacement of loaded/disk binaries.
- PDB has 1,294 document records: 1,293 SHA-256 records and one SHA-1 record for
  Unity's generated `AssemblyMonoScriptTypes.generated.cs`.
- All 1,293 checked-in files match their recorded compilation checksums **exactly
  on disk**. All 1,293 Git blobs match after LF-to-CRLF conversion. None is a
  content mismatch. Local `core.autocrlf` is true and the inspected C# path has
  the Git text attribute.
- The one generated document is absent from the checkout/Git and remains
  unverified. The compiler response file lists 1,293 `.cs` inputs and specifies
  deterministic compilation with portable debug symbols. This cached response
  file was not independently bound to the DLL's build execution.
- Referenced DLLs, full compiler/generated inputs, assets/config and the other
  loaded assemblies were not completely mapped to the selected commit. Thus
  this does **not** change `loaded_source: unknown` in the production checker.

See [source checksum comparison](evidence/source-comparison.json) and
[current live identity / source integrity](evidence/live-identity.json). The
existing four dirty/untracked `tools/device-mcp` files, status and index hash
were unchanged during the live read. No source, asset, scene or package was edited.

## Method and validation scope

A disposable inspection program was built under ignored QA
`.local/provenance-probe/` using the already installed .NET SDK 9.0.306, with an
empty NuGet source list. It reads files with `PEReader`,
`MetadataReaderProvider.FromPortablePdbStream`, `BlobContentId`, module metadata,
CodeView debug entries and PDB document hashes. It never loads/runs game DLLs.
This is an exploratory helper, not a shipped utility or dependency change.

The comparison read committed blobs with `git ls-tree` and `git cat-file --batch`,
hashed materialized files, and explicitly classified exact, line-ending-only,
missing and content-mismatched records. Initial inspection rejected the generated
document's different hash algorithm; inspection identified SHA-1 and compared it
separately rather than silently treating it as SHA-256. No raw source contents
were printed or copied into these evidence files.

The existing fixed readiness probe then ran in memory through the loopback MCP
service, with fresh idle-state checks before/after, and its HotUpdate module ID
matched the inspected disk module. No game methods were invoked. These are
measured observations from this machine, not unit-test results or a general
verified PDB parser. The production identity implementation and its 121-test
checkpoint from PR #9 were not changed; no new runtime tests were needed for
this documentation/evidence increment.

## Session findings

Source plus live type metadata confirm that Net exposes separate transport,
authentication and generation properties. The intended public authentication
flag becomes true only when a nonzero completed generation matches the current
generation. Source `LoginService` writes PlayerID from authentication, but can
retain old player information during reconnect failure. It writes ZoneID = 1;
that field cannot discriminate test environments.

`Nova.NetManager` privately stores its route in `_address`; a saved route alone
does not prove a live connection. A future snapshot must bind sanitized route,
authenticated/connected state and expected player to the same current generation.
The current Editor was not playing, so no authenticated server/account values
were observed and no server environment was inferred from configuration.

## Concrete next action and boundary

The [controlled-build proposal](../../docs/farmqa-controlled-build.md) specifies a
separate client copy, exact commit/Unity/platform, input/output capture, LFS
verification and preservation rules. This gives the next implementation a
reviewable operation instead of a fictional positive provenance result.

The user-provided QA boundary says client checkouts are read-only. A fresh Unity
build requires a writable QA copy for imports, caches and generated outputs, so
that operation awaits explicit authorization. No new client checkout or build
was created in this turn. The source client has LFS assets, Git LFS is installed,
and D: had approximately 283.6 GiB available; final asset availability/build size
still requires checking during preparation.

After a controlled build: implement/verify safe session observation, identify an
authorized test environment/account before any login, and verify physical action
ownership/cancellation before gameplay. No message was sent to a development
task or external system, no new PR was opened, and no deployment was changed.
