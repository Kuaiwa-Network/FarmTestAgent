# Session diagnostic and accepted Spine deferral — 2026-09-17

Implemented a standalone read-only session probe/comparator and verified its
Edit Mode rejection. **Authenticated live verification is NOT RUN.** No gameplay
permission, production integration, login or game actions were added.

The user accepted leaving Spine default settings unchanged for existing content
after the bounded material/texture comparison found no impact, and requested
continuing readiness work. The overwrite remains documented; rendering and
new-asset effects remain untested. This increment did not restore settings or
patch Spine. Architecture and knowledge now reflect that accepted deferral.

The existing controlled-build design already proposed safe session observation.
This increment adds `tools/farmqa_session_identity.py`, the QA-owned C# probe and
a fixed `UnityIdentityClient.session_probe` entry point. It compares explicit
numeric player/route-hash expectations and rejects stale, disconnected, changing,
missing or mismatched identity. No raw route/account/token output is exposed.
The result always remains BLOCKED for gameplay, including a diagnostic match.
It does not relax the request-bound identity checker or alter queue/worker state.

During discovery, the connected Editor was the original
`D:/AgentWorkSpace/Farm/Farm-Client`, commit
`a6dce07592d32b9760d60321118abd496c5bb291`, Unity 2022.3.62f3,
StandaloneWindows64. It had replaced the fresh QA Editor before this increment's
live discovery. The agent did not switch projects or launch/close Unity.
Play Mode was off. Original source status contained the same four device-mcp
local changes; snapshots immediately before/after verification matched exactly.
This is a different build from pinned QA `7dbf23b`; evidence is not relabeled.

Verification:

- Eight initial comparison tests failed because the implementation was absent.
  After implementation and three selection/error cases, all 11 focused tests
  passed. Wrong identity, missing fields, unstable generation, stale/future data,
  redaction, wrong project and replacement instance are covered.
- Full Python suite: **132 tests passed in 14.185 seconds**. No external login or
  game server calls occurred in these tests.
- Unity CodeDOM compiled the complete probe and executed its early Edit Mode
  branch with MCP safety checks enabled. It returned `status: edit_mode` before
  accessing game static state. The standalone CLI also returned this observation,
  `session_match: unknown`, `execution_enabled: false`, exit code 2.
- Final live readiness probe: Play Mode off, no compilation/import, zero Console
  errors. Original client source/index/dirty-file hashes unchanged.
- Read-only code review found no blocking issues and confirmed reflected schema
  against pinned source. The C# authenticated branch, including URI filtering,
  reflected reads and reconnect stability, remains source-reviewed only. Python
  fixture matches are not a live session verification.

Redacted evidence: [verification.json](evidence/verification.json). Private
responses, original before/after snapshots and full test output are in the main
QA checkout's `.local/session-identity/`. No secrets are in this report.

Next: verify the authenticated path with an explicitly authorized test
account/environment and agreed build. No account/environment was selected here.
Before autonomous actions, establish physical ownership/cancellation and the
remaining build/session evidence. Spine defaults alone are not a prerequisite
for this next session check. See [usage](../../tools/README-farmqa-session-identity.md).
