# Spine settings preservation during import

Purpose: detect a fresh Unity import replacing checked-in Spine preferences with
legacy/default values, and distinguish current-Editor recovery from prevention.

Known observation: client `7dbf23b`, Unity 2022.3.62f3 / StandaloneWindows64,
Spine package `eb588ecd57`. See the
[investigation](../../reports/2026-09-17-farmqa-import-drift/report.md).

## Preconditions

- Use an authorized writable QA copy at an explicitly pinned revision. Original
  client/server checkouts remain read-only. Preserve existing local changes.
- Record the checked-in Spine settings, package identity, input hashes and
  relevant EditorPrefs key presence. Do not change machine-wide preferences.
- Keep one QA Editor, Play Mode off, no active tests or unsaved scene state.
- A new empty-Library run requires its own preserved input/output evidence;
  never delete the existing evidence or Library merely to execute this scenario.

## Fresh-import regression (not yet executed after a fix)

1. After normal shutdown of the previous QA Editor, directly launch the pinned
   copy visibly with an empty Library and private logs. Do not use the previously
   crashing EditorApplication.OpenProject route.
2. After import is idle, compare `Assets/Editor/SpineSettings.asset` bytes with
   the input hash. Inspect any CreateAsset-during-import warning and its stack.
3. Run `tests/probes/spine-import-state.cs.txt` through the existing Unity MCP
   execute_code tool with safety checks enabled after selecting the exact instance.
4. Require the intended loaded shader/preset settings, same expected asset GUID,
   no tracked import-config drift, zero Console errors and Play Mode off.
5. Validate affected imported assets before accepting a build baseline. Settings
   alone are not proof that texture/material imports used the intended inputs.

PASS requires an actual fresh-import run preserving the inputs. Do not count a
working copy restored after import, a warm reimport, or mocked tests as that pass.

## Current-Editor recovery (observed PASS, narrower scope)

Preserve the changed file, validate the target, and restore only the exact pinned
settings bytes after the package is available. Force a synchronous import of that
asset, read both loaded fields and cached-asset correspondence, repeat once and
rehash. Record each restoration as an intervention. Compare all tracked inputs
and the original-client snapshot. Stop on unexpected drift or new errors.

This recovery must not enable gameplay or relabel an older manifest. It leaves
fresh-import prevention and effects on already-imported assets unresolved.


## Latest replay — 2026-09-17

Fresh independent copy at the same commit: settings preservation **FAIL**, with
fallback shader/empty preset and CreateAsset-during-import evidence. Settings were
not restored. The read-only `spine-atlas-imports.cs.txt` probe compared 169 atlas
rows and 170 material/texture references with the recovered-copy baseline; all
sampled fields, including texture content hashes, matched. That bounded structural
comparison passes, while rendering/new-asset effects remain untested. See the
[fresh-run evidence](../../reports/2026-09-17-farmqa-fresh-import/report.md).
