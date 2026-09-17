# FarmQA isolated Editor import and compilation — 2026-09-17

**Compilation: PASS with warnings. Clean build provenance: BLOCKED. Gameplay:
not run.** The user approved a separate writable QA client copy and compilation
with Play Mode off. The original checkout, including its four existing local
changes and Git index hash, is unchanged.

## Target and method

- Client commit: `7dbf23bef80c660ceb5d384c2e99cff029e5b79a` (detached).
- Original: `D:/AgentWorkSpace/Farm/Farm-Client` (read-only throughout).
- QA copy: `.local/clients/farmqa-7dbf23b` under the main FarmTestAgent checkout.
- Unity: `2022.3.62f3`, Windows Editor, `StandaloneWindows64`.
- Live instance: `farmqa-7dbf23b@66bddd43c432dae8`.
- Private evidence: `.local/controlled-build/` under the main QA checkout.

Cloned independently with `git clone --no-hardlinks --no-checkout`, then checked
out the exact commit with LFS smudging disabled. No source worktree metadata,
dirty working files or Library cache was copied. There are no Git alternates.
All 3,481 unique LFS objects were available locally; each object and all 3,593
materialized files were hash-verified. LFS needed no network download. Unity
resolved its packages normally; this is not a claim of an entirely offline build.
The initial checkout was clean. The tracked input manifest contains 15,884 files;
there are no Git submodules or local `file:` package references. The package lock
records 9 Git, 22 registry, 3 embedded and 40 built-in packages.

Before switching projects, inspected the original Editor for active compilation,
Play Mode, unsaved scene changes and an open prefab stage. None blocked the
switch. Opened the isolated project with a private log and Win64 target. This was
an interactive Editor import/script compilation, **not a player build or test
run**. The CLI flags are documented in the
[Unity 2022.3 manual](https://docs.unity.cn/2022.3/Documentation/Manual/EditorCommandLineArguments.html).

## Verification

The fresh MCP observation shows one connected Editor, the exact isolated project,
idle compilation/import, Play Mode off, no running tests and an unsaved empty
scene with `isDirty=false`. Console retrieval returned **0 errors, 550 warnings**.
The private Editor log had no `error CS...` or `Shader error` lines. Warnings
were retained; zero errors does not establish correct rendering or gameplay.

All four selected modules—HotUpdate, AOTScripts, Nova.Runtime and
MCPForUnity.Editor—have matching live/disk module IDs and matching DLL/PDB debug
identities. HotUpdate exposes GameTestDriver. For those modules respectively,
1,293 / 19 / 15 / 302 available source documents match their PDB checksums, with
zero mismatches. Each PDB also references one generated
`AssemblyMonoScriptTypes.generated.cs` document absent from disk.

The private output manifest hashes 113 DLLs and their available PDBs from the
stable ScriptAssemblies snapshot before the live probe. Probe execution can add
transient assemblies, so this is not a permanent directory-size assertion.
The HotUpdate compiler record hashes its response file and 258 inputs: 253
references, 2 analyzers, 1 additional file and 2 compiler binaries. None were
missing. This compiler record covers **HotUpdate**, not every assembly invocation.
Full paths, response-file contents and raw logs stay private. Manifest hashes and
allowlisted results are in [build-summary.json](evidence/build-summary.json);
the live observation is in [live-identity.json](evidence/live-identity.json).

## Import changes and blockers

Two of the 15,884 tracked inputs changed during import:

| File | Observed change |
|---|---|
| `.vscode/settings.json` | `dotnet.defaultSolution` changed |
| `Assets/Editor/SpineSettings.asset` | `defaultShader`: `Universal Render Pipeline/2D/Spine/Skeleton` → `Spine/Skeleton`; `textureSettingsReference`: package StraightAlphaPreset path → empty |

The Spine settings affect import configuration. Their exact before/after hashes
are recorded. No changes were reverted or repaired to manufacture a clean result.
This is an environment/import observation; no gameplay defect or root cause has
been established. The working copy remains dirty and must not be represented as
an unmodified build of the selected commit.

Clean provenance remains BLOCKED by that drift, absent generated sources, and
incomplete compiler/asset evidence for the entire project. The existing identity
collector remains unchanged and continues to block gameplay. No positive gate,
server/account identity, login, Play Mode, scene save or gameplay action was added.

## Operational changes and recovery

The original Editor closed and the isolated Editor opened; only one QA Editor
was used. Its previous local MCP server ended during the switch. Automatic
approval review rejected starting the replacement server, with stated reason
“blocked by policy.” The user clicked Start Server in Unity; a fresh MCP session
then connected successfully and supplied the final evidence. This blocker was
resolved manually, not bypassed. The FarmQA receiver and deployment checkout
were not changed or restarted by this build work.

For future work, rediscover the actual instance and project before acting. Reuse
the private manifests only as historical evidence, and rehash current inputs and
outputs. Keep this QA copy and private logs; do not automatically reset, delete,
switch back to the original client or start Play Mode.

## Next steps

1. Investigate why this package/import changed the two tracked settings. Preserve
   the current evidence and determine whether a documented, isolated import
   procedure can retain the pinned settings. Do not edit game source to hide it.
2. Capture the remaining compiler/generated-source and imported-asset evidence
   before implementing a positive provenance check. Scope any such check honestly
   as a trusted-machine operational record, not reproducible-build attestation.
3. Implement the proposed safe session observation only after the actual build is
   identified. A positive server/account check still needs an authorized login;
   physical controller ownership and bounded cancellation remain separate gates.

No application code changed in this increment. Validation was the actual Editor
import, fresh live probe, Console read, file hashes and DLL/PDB metadata checks;
the Python test suite was not rerun for these documentation/evidence changes.
