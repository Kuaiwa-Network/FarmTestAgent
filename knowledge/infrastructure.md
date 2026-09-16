# Infrastructure knowledge

The entries below describe the earlier Mac run. For the current Windows machine,
see the [2026-09-16 live Editor inspection](../reports/2026-09-16-unity-readiness/report.md).
Observed: Unity 2022.3.62f3 is running on Farm-Client revision `7dbf23bef80c660ceb5d384c2e99cff029e5b79a`,
instance `Farm-Client@6d4c4b2750085821`, target StandaloneWindows64. StartScene is clean,
Play Mode is off, and live error/warning reads are empty. The loaded HotUpdate module
ID is `58847d20-a524-43d9-b9da-3e2c9a1bc5ec`; it contains GameTestDriver. Loaded/disk
module IDs match, but a reproducible source-to-build relationship was not verified.
Native screenshots and read-only MCP inspection succeeded; gameplay remains disabled.
The [earlier Windows preflight](../reports/2026-09-16-farmqa-followup-preflight/report.md)
found no ADB devices and an existing broker with ownership unestablished. Opening
Unity later replaced a competing ADB server; device availability was not rechecked.
No game login/session has been verified. Do not transfer the Mac's loaded-build
identity or driver observations to this checkout.

All entries last verified/reviewed 2026-09-16. Client source scope is revision
`688da4652c9c2c3b5702c8e99d81e1480df419f7` unless otherwise specified.
Evidence root: `../reports/2026-09-16-initial-learning/evidence/`.

| ID / status | Claim and prerequisites | Platform/build and evidence |
|---|---|---|
| I01 observed | UnityMCP connected to `Farm-Client@edc12837aaf5486f`; actual root is the workspace client, not the reference worktree. Re-query each run. | OSXEditor 2022.3.62f3; `preflight0.json`, `editor-identity.json` |
| I02 observed | Both checkouts had the same HEAD; 21 requested guidance/driver/scenario files matched SHA-256. This does not prove every file or loaded artifact matches. | `source-identity.json`; scoped tracked diff was empty |
| I03 observed | Loaded GameTestDriver is callable via synchronous `execute_code` (CodeDom). Assembly MVID recorded; app version 1.0 and all-zero Editor build GUID are insufficient build identifiers. | MVID `8e0f3b3d-e2b9-4030-93c8-aa4173206538`; `editor-identity.json` |
| I04 observed | `DumpUtil` loses current protobuf properties, including slot/crop state. Synthetic populated objects dump as `{}` / `[{}]`; do not use these as zero/empty state. | Loaded Editor assembly; `serializer-probe.json` |
| I05 observed | Three isolated pointer tests passed: delivery, covered target, untouchable target. Requires PlayMode and live frames. This is not farm gameplay coverage. | `pointer-tests-result.json`; 3/3 passed |
| I06 observed | Broker launches via existing Python dependencies and advertises 22 tools including pointer verbs. Short status probe saw no registered build. It was terminated after inspection. | Host Python 3.13, FastMCP response 1.28.1; `broker-preflight-retry.json` |
| I07 observed | ADB 37.0.0 is installed at `~/Library/Android/sdk/platform-tools/adb`; device enumeration returned an empty list. Device state must be rechecked, not assumed permanent. | Host preflight; `environment.json` |
| I08 observed | Four existing broker pointer tests pass with mocked `_call`; they prove argument forwarding, not socket/device/input delivery. | `broker-pointer-tests.txt` |
| I09 observed | `qa_run.py` accepts MainView without verifying requested identity, accepts empty-slot watering, and converts unreadable crop records to zero. Reproduced twice offline, using synthetic fixtures. | `runner-audit-1.json`, `runner-audit-2.json` |
| I10 observed | Runner rejects `click`; only rose-lifecycle has its required steps block. Parseability alone does not prove that scenario works. | Same offline audits |
| I11 observed | `compile_cs._game_dll_dir()` selected StandaloneOSX while Android artifacts also existed. It has no per-device build selection. | Host; `environment.json`, `local-artifacts.json`; source `compile_cs.py:29,57` |
| I12 inferred | Device hello identifies product/version/platform/launch label but lacks immutable source, config and hot-update hashes or capabilities. Device label is per launch, not a stable hardware/build identity. | `DeviceAgent.cs:145`, `server.py:137`; no Android agent observed |
| I13 inferred | Simulation covers one in-game pointer, not Android OS touch delivery, native keyboard, pinch or system Back. | `docs/pointer-simulation.md`, `PointerSimulation.cs`; current API scope |

Android APKs and player DLLs exist locally but are older on-disk artifacts. Their
hashes are inventoried; neither their installed status nor their `FARM_TESTHOOKS`
capability nor their equivalence to this Editor assembly was established. Do not
reuse July device validation as current build validation.

`DumpModel("player")` follows public fields and PlayerModel contains `Token`.
Use selective account/player/zone reads without Token; a remembered server preference
is not proof of the connected server. No player/session data was dumped in this run.
