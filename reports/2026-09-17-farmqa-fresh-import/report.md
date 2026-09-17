# Fresh import: Spine settings regression reproduced — 2026-09-17

**Latest result: FAIL for settings preservation; PASS for automatic MCP connection
and the bounded structural asset comparison.** The user resumed the work after
Editor recovery and manually closed the recovered Editor. Shutdown completed
without a crash. A direct visible launch of the fresh copy then completed import;
this supersedes the earlier “fresh import did not start” status below.

The target was the independently cloned `farmqa-fresh-7dbf23b` QA copy, pinned to
`7dbf23bef80c660ceb5d384c2e99cff029e5b79a`, Unity 2022.3.62f3,
StandaloneWindows64. Immediately before launch, all 15,884 tracked input hashes
still matched preparation and Library was absent. No Library was copied or
removed. The fresh Editor launched as PID 2820, with Play Mode off. Its plugin
started the local MCP server and connected automatically; no Start Server click
or separate server launch was needed. Fresh MCP discovery found exactly one
connected Editor at the expected project path.

Import again overwrote `Assets/Editor/SpineSettings.asset`: the shader became
`Spine/Skeleton` instead of `Universal Render Pipeline/2D/Spine/Skeleton`, and the
StraightAlphaPreset path became empty. The log again records Spine preferences
creation during import. Both legacy EditorPrefs keys were absent; the live
serialized settings and cached asset agreed with the overwritten values. The
expected shader and preset assets were available. No restoration or package fix
was applied to this fresh copy. The changed settings are preserved as evidence.

All 15,884 tracked files were compared after import. The only other byte change
was the VS Code solution-name setting. Original-client and recovered-QA-copy
commit, status, dirty-file and Git index snapshots remained unchanged throughout
this resumed run. The original client was already at `a6dce07592d32b9760d60321118abd496c5bb291`
at this run's start; it is not the pinned QA target.

The read-only atlas probe found 169 Spine atlas assets, 170 material references
and 170 unique textures. Every returned row matched the recovered-copy baseline,
excluding the top-level project root: paths, supported URP shader, dimensions,
format, texture content hash and sampled importer settings. No missing references
or structural problems were found. This narrows the observed impact to settings
in this comparison; it does not prove rendering, new-asset imports or gameplay.

A live probe confirmed idle Edit Mode and a clean scene; the Console error read
returned zero entries. The first editor-state resource was marked stale despite
idle flags, so it was not treated as a readiness pass; the subsequent guarded
Editor probe supplied the live compilation/import/Play Mode flags. The four core
loaded MVIDs match the fresh DLLs and their DLL/PDB identities match. Source
checksums match 1,293 HotUpdate, 19 AOTScripts, 15 Nova.Runtime and 302
MCPForUnity.Editor documents, with zero mismatches. Each PDB still names one
unavailable Unity-generated `AssemblyMonoScriptTypes.generated.cs` document.

The private build capture includes 113 compiler response files and 37,250 parsed
source/reference/analyzer/additional-file entries with no missing referenced
files, plus 113 output DLL hashes and PDB hashes. This post-import capture does
not establish complete compiler/generated-source provenance. Tracked import
settings drift and unavailable generated documents keep complete provenance
BLOCKED; no positive manifest or gameplay permission was issued.

Redacted evidence is in [verification.json](evidence/verification.json).
Private manifests, live responses, console result and module/atlas comparisons
remain under the main QA checkout's `.local/fresh-import/`. The fresh Editor is
left open in Edit Mode with the failed settings preserved; the recovered copy is
closed and unchanged. No game source edits, login, gameplay, bridge deployment
changes or PR merge occurred.

Original proposed next step (superseded by the user decision below): report the
reproduced initialization defect to the client/package owner.
A candidate fix should distinguish “settings file exists but AssetDatabase is
not ready” from “settings absent,” avoiding fallback CreateAsset over the pinned
file. This is a source-grounded suggestion, not an implemented or verified fix.
After an authorized fix, repeat this empty-Library scenario in another preserved
QA copy and resolve generated-input provenance before accepting a clean baseline.
Original client/package source remains read-only here.

## Subsequent user decision

The user accepted deferring the defaults issue for existing-content testing and
requested continuing readiness work. Leave settings unchanged. The structural
comparison found no impact in its sampled fields; rendering/new-import behavior
remains untested. Revisit on new Spine imports or observed visual differences.
No package fix is required before continuing the session diagnostic; historical
FAIL/BLOCKED evidence remains unchanged.

# First attempt: project-switch shutdown crash

**BLOCKED: Unity crashed during the requested project switch. The fresh import
did not start.** This is an operational failure, not a successful import test.
The user reported the crash; investigation confirmed it. Do not retry the switch
automatically or present the prepared copy as a tested build.

PR #11 was verified merged at `3256225`. A separate independent client clone was
prepared at `.local/clients/farmqa-fresh-7dbf23b` under the main FarmTestAgent
checkout, pinned to `7dbf23bef80c660ceb5d384c2e99cff029e5b79a`. Its 3,593 LFS
files and 15,884 tracked inputs were hashed; the checkout was clean and Library
was absent. The existing recovered QA copy was preserved.

Before switching, the recovered Editor was idle with Play Mode off, no running
tests, one clean scene and no prefab stage. A read-only snapshot found 169 Spine
atlas assets and 170 material/texture references, all with the intended supported
URP shader and available textures/importers. This is structural evidence only;
no fresh comparison or rendering test ran. The QA baseline suite passed 121 tests.

The agent scheduled `EditorApplication.OpenProject` to close the recovered QA
project and open the fresh copy with a separate log and Win64 target. The Editor
did not complete that transition while in the background. After the agent brought
the existing Unity window forward, window activation timed out, the old window
disappeared, and Unity processes subsequently exited. The original Editor log
contains shutdown cleanup followed by `Crash!!!`. Windows Application events
1000/1001 also record Unity crashes at approximately 14:08 local time. The exact
native failure cause is not established; do not assume the API call or window
activation alone identifies the underlying engine defect.

No fresh Editor log or Library was created. The agent paused the fresh-import
work after the user's correction and did not retry the launch/switch. Unity was
closed at the last observation. Revalidate process state before any recovery.

Both the original client and the recovered QA copy were compared with their
pre-attempt snapshots after shutdown: tracked status, dirty-file hashes and Git
index hashes were unchanged. No Play Mode, source fix, scene save, asset repair,
deployment restart or gameplay operation was performed in this attempt.

Private evidence is in the main QA checkout's `.local/fresh-import/`: preparation
and input manifests, recovered atlas snapshot, switch result, preserved crash
tail, post-shutdown snapshots and `failure-summary.json`. Raw crash diagnostics
remain private. The existing controlled-build log also retains the shutdown
record. No positive build manifest was generated for the fresh copy.

Recovery must first restore the intended Editor availability and inspect the
shutdown failure. Preserve both copies and all logs; do not delete a Library or
repeat this project-switch route to manufacture a fresh-import result.
