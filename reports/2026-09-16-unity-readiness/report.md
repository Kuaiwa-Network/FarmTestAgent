# Windows Unity readiness — 2026-09-16

Outcome: **PASS for read-only Editor readiness. Gameplay remains disabled.**
The user approved opening the existing Farm-Client Editor and checking its
connection, loaded assemblies, console, and screenshot access, with Play Mode off.

## Actual target and evidence

- Project: `D:/AgentWorkSpace/Farm/Farm-Client`, Git revision
  `7dbf23bef80c660ceb5d384c2e99cff029e5b79a`. The existing client checkout was not
  fetched, switched, or updated. Its cached tracking state was 14 commits behind
  `origin/main`; this does not establish the current remote revision.
- Editor: `D:/Program/UnityEditor/2022.3.62f3/Editor/Unity.exe`, version
  `2022.3.62f3` / `96770f904ca7`, PID 588, WindowsEditor, active build target
  `StandaloneWindows64`. Started at 20:46:45 Asia/Shanghai.
- Live instance: `Farm-Client@6d4c4b2750085821`. MCP discovery returned one
  connected Editor. The instance was selected explicitly for subsequent reads.
- Scene: `Assets/StartScene.unity`, not dirty. Live resource and reflection reads
  both reported Play Mode off, no pending Play Mode transition, no compilation or
  asset update. The resource reported idle, ready for tools, and no running tests.
- The loaded `HotUpdate`, `AOTScripts`, `Nova.Runtime`, and `MCPForUnity.Editor`
  module IDs matched the corresponding on-disk DLL metadata. The loaded
  `HotUpdate` module ID is `58847d20-a524-43d9-b9da-3e2c9a1bc5ec`, and it contains
  `Farm.Core.TestDriver.GameTestDriver`. No game-driver method was invoked.
- Console: UI counters showed zero errors and zero warnings. The subsequent MCP
  `read_console` error/warning query returned zero entries. Logs were not cleared.
- Native Computer Use captured the Editor and Console. This verifies screenshot
  access and basic Editor-window navigation in this task, not gameplay input or
  unattended access from every future inbox task.
- The client status and SHA-256 hashes of its four existing modified/untracked
  files matched before and after. No authored changes were made to the client.

Evidence: [baseline](evidence/before.json), [launch](evidence/launch.json),
[startup log summary](evidence/startup-log-summary.json),
[initial connection panel](evidence/mcp-panel.jpg),
[Editor and Console screenshot](evidence/editor-console.jpg),
[live Editor reads](evidence/live-editor.json), and
[final client/assembly integrity](evidence/final-integrity.json).
The intermediate [process inventory](evidence/after.json) precedes the successful
loaded-assembly probe; its `loaded_identity_verified: false` reflects that earlier
point in time, not the final outcome.

Evidence validation caught JPEG captures initially saved with a `.png` suffix;
the filenames were corrected to `.jpg` without changing the image bytes. An
expired screenshot reference also required a fresh observation before UI navigation.

## Connection and state changes

The existing Editor package is MCP for Unity 10.2.0. Codex's existing Unity MCP
configuration points to `http://127.0.0.1:9090/mcp`. Initially no server listened
there and the panel showed No Session. The matching installed server's offline
help command succeeded; no package download or upgrade was requested.

Automatic approval review rejected this task's attempt to launch the local server
with the message `blocked by policy`, without a more specific reason. That command
did not create the requested private PID/log files. No alternate launch was tried.
A separate server process subsequently appeared at 20:51:49 (PID 23112), and the
Editor connected at 12:52:51 UTC. This task did not establish who started it.
Read-only MCP calls then succeeded against that existing loopback service.

This task's tool catalog did not expose Unity tools directly. Inspection used the
installed MCP Python SDK against the configured endpoint: initialize, discover
resources/tools, read instances/state/project info, select the actual instance,
run the small [identity probe](../../tests/probes/editor-readiness.cs.txt), read
console errors/warnings, and read state again. The identity probe compiled in
memory through the existing `execute_code` tool with safety checks enabled. It
only read Editor metadata and assembly identity. No client script was created.

Opening Unity necessarily updated local Editor/cache state. Its Console reported
that it terminated a competing ADB server from the other SDK, and the MCP package
logged `StartupConfigRewrite` refreshing four client configurations. These were
startup actions, not explicit commands issued by this task; the exact configuration
file changes were not audited. The existing device broker at port 8973 and FarmQA
receiver at port 8765 retained their prior PIDs, 21904 and 8848 respectively.

The Editor and subsequently connected MCP server remain running. No new process
supervision, network exposure, firewall change, game login, scene save, Play Mode,
gameplay test, build, or deployment was performed. Raw Editor logs stay under
ignored `.local/unity-readiness/`; only allowlisted observations are tracked.

## Limits and next steps

Loaded module IDs and disk hashes identify the inspected assemblies; they do not
prove a reproducible build from the current Git revision, nor the identity of a
future downloaded hot update or Android install. StartScene's edit-time image is
not evidence of a connected game session. Historical Mac driver findings remain
open until revalidated on this Windows build.

Before gameplay: verify actual active-task interruption (Linear Stop currently
suppresses replies but cannot interrupt Codex), establish exclusive controller
ownership, and identify an authorized test account/environment. Then validate
safe session/state observations before the bounded one-plot learning scenario.
Do not enable gameplay merely because this readiness inspection passed.

The next bounded bridge check is manual interruption of a harmless waiting inbox
task, verifying an actual `interrupted` outcome and suppressed Linear reply.
That would verify the documented manual fallback, not add automatic interruption.
The supported automatic interruption path remains a separate prerequisite.

Only QA evidence, knowledge, and a read-only probe changed in this repository.
No bridge runtime change was required, no PR was merged, and these new artifacts
are committed locally without pushing an unrelated update to the Stop PR.
