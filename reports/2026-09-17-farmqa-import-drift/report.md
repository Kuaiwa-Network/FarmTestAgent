# Spine import drift investigation and isolated recovery — 2026-09-17

**Cause identified; recovery PASS for the current Editor. Fresh-import prevention
and complete build provenance remain BLOCKED.** PR #10 is merged at `041fd02`.
This investigation starts from that merge on `codex/farmqa-import-drift`.

## Target and scope

Client `7dbf23bef80c660ceb5d384c2e99cff029e5b79a`, isolated QA copy
`.local/clients/farmqa-7dbf23b` under the main FarmTestAgent checkout; Unity
2022.3.62f3 / StandaloneWindows64. Exact live instance:
`farmqa-7dbf23b@66bddd43c432dae8`. Play Mode stayed off. The original
`D:/AgentWorkSpace/Farm/Farm-Client` checkout and its pre-existing changes remain
unchanged. No game/package source or machine-wide Editor preferences were edited.

The user approved proceeding with investigation after the controlled-build PR.
Recovery was limited to restoring the pinned Spine settings in the already
authorized writable QA copy. Private backups and records are under the main QA
checkout's `.local/import-drift/`; first-build evidence was preserved.

## What wrote the settings

The first-import log contains a Unity warning that `AssetDatabase.CreateAsset`
ran during import. Its stack is:

`TextureModificationWarningProcessor.OnWillSaveAssets` →
`SpineEditorUtilities.Preferences` → `SpinePreferences.GetOrCreateSettings` →
`AssetDatabase.CreateAsset`.

The [allowlisted log excerpt](evidence/import-stack.txt) places this immediately
before the recorded import of `Assets/Editor/SpineSettings.asset`. The installed
package is `com.esotericsoftware.spine.spine-unity@eb588ecd57`:

- `Utility/SpineEditorUtilities.cs:565` reads preferences before checking whether
  any saved path is an atlas texture. Thus even an unrelated asset-save callback
  can initialize Spine preferences.
- `Windows/SpinePreferences.cs:213-230` tries loading/finding the preferences
  asset. If neither returns an object, it creates an instance, copies legacy
  preferences and creates the asset at the fixed path. It does not first check
  whether that file already exists on disk but is unavailable to AssetDatabase.
- `Utility/Preferences.cs:234-246` reads `SPINE_DEFAULT_SHADER` and
  `SPINE_TEXTURE_SETTINGS_REFERENCE` from EditorPrefs, falling back to
  `Spine/Skeleton` and an empty preset reference.

The stack establishes that the create path executed during this import. The
source and before/after bytes explain the overwrite. **Inferred timing cause:**
the checked-in settings were not yet available through AssetDatabase during the
save callback. The exact null return values were not instrumented at the time;
no second empty-Library import was performed, so frequency is unknown.

The live read-only probe found both legacy keys absent, the recreated asset
containing those fallback values, and Spine's cached settings referencing that
same asset. The desired URP shader and Straight Alpha preset both load in the
current Editor. Their current availability does not establish first-import
ordering. Three relevant Spine source checksums match its PDB, the DLL/PDB debug
identities match, and the loaded/disk MVID matches; see
[source identities](evidence/source-identities.json). This ties the inspected
write path to the loaded package without claiming full-project provenance.

## Separate VS Code setting change

`dotnet.defaultSolution` changed from `Farm-Client.slnx` to
`farmqa-7dbf23b.slnx`; it is the only changed JSON key. In installed
`com.unity.ide.visualstudio@2.0.27`, `VisualStudioCodeInstallation.cs:430-436`
patches this setting to the generated solution filename. Project generation uses
the project directory name. This is a source-explained IDE setting change,
separate from Spine's import configuration. No VS Code patch-call stack was
captured, so attribution is source-inferred. It is preserved, not silently
excluded from the tracked-change inventory.

## Recovery and verification

1. Saved both changed files and the original-client snapshot privately.
2. Revalidated the exact isolated project, a fresh idle Editor state, no running
   tests and Play Mode off.
3. Restored **only** `Assets/Editor/SpineSettings.asset` from the pinned Git blob,
   requiring an exact match to the first-build input SHA-256. The file uses
   `eol=lf`; an initial CRLF candidate failed the hash guard before any write.
4. Forced a synchronous import of that single asset. The read-only probe then
   confirmed the intended values on the loaded asset and its matching cached
   Spine reference. No legacy preference was set.
5. Repeated the same targeted import once. State and bytes remained stable;
   Console returned zero errors and the Editor remained idle with Play Mode off.
6. Rehashed all 15,884 tracked inputs. Spine matches the original input hash
   `4d05acd845fa79d5b0c2fc1e4a0db97b70d9072797b29747af13b439e9d5af90`.
   Only `.vscode/settings.json` differs. Original client status, dirty-file hashes
   and index hash match the pre-investigation snapshot.

Evidence: [before](evidence/live-before.json), [after](evidence/live-after.json),
[restoration](evidence/recovery.json), [repeat import](evidence/repeat-import.json),
[tracked inputs](evidence/tracked-after.json). The reusable read-only
[probe](../../tests/probes/spine-import-state.cs.txt) deliberately avoids Spine's
mutating preferences getter. The [scenario](../../tests/scenarios/spine-import-drift.md)
defines the missing fresh-import regression separately from this recovery.

Baseline QA suite: `python -m unittest discover -s tests -q` — **121 passed** in
14.067 seconds. The new probe was compiled/executed in the actual Editor before
and after recovery. No runtime implementation changed; these results do not
establish gameplay correctness.

## Limits and next work

Restoring settings does not retroactively validate assets imported while fallback
settings were active. No full asset reimport, fresh-cache reproduction, package
fix or complete manifest regeneration was performed. The older controlled-build
manifest remains historical; it cannot be relabeled as the recovered run.

Next, establish an import procedure that preserves the pinned preferences on a
fresh cache, or report/fix the package initialization through the client owner's
workflow. A fix must distinguish an existing-but-unavailable settings file from
an absent file and defer dependent work safely; merely returning null would
break callers that immediately dereference preferences. Do not patch the cached
package in place or mask the issue with machine-wide fallback preferences.

Then validate affected imported assets and regenerate the scoped build manifest.
Capture remaining generated/compiler inputs before enabling positive build
identity. Server/account identity, physical controller ownership and cancellation
are still separate gates. No login, gameplay, deployment change or PR push was
performed in this increment.
