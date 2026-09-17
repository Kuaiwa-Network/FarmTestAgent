# FarmQA Linear integration

Last reviewed 2026-09-17. Load this for mention-service work, not gameplay rules.
Start with the [consolidated architecture](../docs/farmqa-architecture.md) for
the current component boundaries, memory locations, and implementation gates.
The dated sections below retain historical verification checkpoints.

| Claim | Prerequisites / evidence | Platform/build | Status / verified |
|---|---|---|---|
| Agent name is **FarmQA**, invoked as **@FarmQA**, with no space. Fixed reply remains the default/rollback mode; this machine now uses the explicitly requested Codex bridge. | User's later request to forward messages into a Codex app session; `tools/linear_farmqa.py`. | Windows deployment | user-confirmed, 2026-09-16 |
| The private OAuth app is created and installed in Kuaiwa AI (`kuaiwagames`), with `read,write,app:mentionable`, client credentials, and only Agent session events. | User explicitly confirmed creation; app settings and live API identity in Windows report. | Linear / Windows deployment | observed, 2026-09-16 |
| Installed-app access is restricted to **Only select teams: 农场**. | Saved admin UI setting; fresh app token reports only Farm team. | Linear / `linear-identity.json` | observed, 2026-09-16 |
| User mention and follow-up on FARM-1188 produced two exact visible replies and a completed session, matching both local `sent` records and actual Linear activity IDs. | Browser agent chat and `live-delivery.json`. | Windows 11 x64 / Python 3.14.3 | observed, 2026-09-16; mention and follow-up both pass |
| Agent follow-up type is nested under `agentActivity.content.type`. | Published SDK schema; corrected local fixture. | Linear API schema | observed in schema, local replay, and live follow-up, 2026-09-16 |
| Original local tests pass; Windows listener exclusivity defect was reproduced and fixed. | 13 passing tests, including second-bind regression. External Linear calls mocked. | Windows 11 x64 / Python 3.14.3 | observed locally, 2026-09-16 |
| Trusted TLS, external HTTPS reachability, and invalid-signature rejection passed. | TLS certificate check, two independent Check-Host nodes, public POST returning 401 with empty ledger. | Current Windows quick tunnel | observed, 2026-09-16; recheck after tunnel restart |

Use [setup and operations](../tools/README-farmqa.md), the
[mention scenario](../tests/scenarios/farmqa-mention.md), and the
[Windows deployment report](../reports/2026-09-16-farmqa-windows/report.md).
Keep credentials and the event DB in ignored `.local/farmqa/`; never put them in
knowledge or reports. Windows private storage requires NTFS ACLs; POSIX mode bits
alone are insufficient. Access tokens remain in memory.

Current app user: `e5a8c16d-9f85-4123-acf5-94e41c3304d5`.
Workspace: `ff27325f-34a2-4e64-be44-5746fd1b3ea3`.
Farm team: `9676b5f9-eff3-485b-80ed-900ed137e21a`.
The receiver binds `127.0.0.1:8765`; VisualSVN continues to own port 443.
`FarmQA-Receiver` and `FarmQA-Tunnel` are current-user interactive scheduled tasks.
The temporary tunnel is the user's selected connection-test route; its hostname
changes when its child process restarts. Update Linear's webhook URL afterward.
The PC must be awake and the Windows user logged in. See the report for the current
run's endpoint; do not reuse historical Mac endpoints.

PR #1 was already merged by `dunadain` at 08:03:01 UTC on 2026-09-16 (`fc1e202`)
before this Windows session; no merge was performed by the deployment agent.
The deleted branch's fetched PR head `77cbcbc` has the same tree as that main
commit. Windows/bridge work was merged in [PR #2](https://github.com/Kuaiwa-Network/FarmTestAgent/pull/2)
by `dunadain` at 11:33:58 UTC on 2026-09-16, producing `e35cd54`. The deployment
agent performed no merge. Follow-up inspection is on `codex/farmqa-verification-followup`.
Do not merge future PRs unless requested.

The original fixed-reply live mention and follow-up both pass. Never infer delivery success from
HTTP 200 or `/health`. Uncertain send outcomes are
not automatically retried. Duplicate/restart delivery behavior is locally tested,
not established by a real Linear retry. No gameplay, issue creation, game workers,
or suite scheduling are enabled, and no gameplay coverage is claimed.

## Codex forwarding increment

The user subsequently requested forwarding messages into a Codex app task.
The destination is **FarmQA Linear inbox**, task
`01a0a9da-3777-7640-b19c-1aa1646ba210`, on this Windows host. It uses a Codex-managed
worktree. Requests and final answers now use Codex model turns; no OpenAI API key
or standalone `codex exec` worker is configured.

`tools/farmqa_codex.py` talks MCP stdio to the installed Codex app-tools plugin.
That plugin delivers messages to the running desktop app over its local pipe.
The CLI's separate default daemon socket was unavailable and is not used.
Two real adapter-to-app tests verified message delivery, preserved conversation
context, and read-only Computer Use discovery through `@oai/sky`. This is not
proof of successful app clicking or gameplay. The live ordinary-comment mention
on FARM-1188 also passed: Linear reused the existing session (`prompted` event),
and the exact Codex final reply was visibly delivered in 8.056 seconds, matching
the API activity and `sent` ledger record. A new `created` session and follow-up
subsequently passed on FARM-1186, in 11.460 and 8.137 seconds respectively; see the
[follow-up report](../reports/2026-09-16-farmqa-followup-preflight/report.md).
The initial round trip's redacted verification is recorded in the
[bridge report](../reports/2026-09-16-farmqa-codex-bridge/report.md).

The original deployment shared one dedicated Codex task across sessions. The
session-routing increment below supersedes that default on this machine for new sessions.
The app must remain running. Its local pipe/runtime paths are installation-specific;
rebind after an app restart/update if the connection changes. Keep `.local/farmqa/codex.json`
private. Bridge prompts/final text are temporarily stored in the private SQLite
ledger, omitted from logs/status/reports, and cleared from active rows after
confirmed Linear delivery. Ambiguous dispatch or reply sends are not retried.

The [follow-up preflight](../reports/2026-09-16-farmqa-followup-preflight/report.md)
rechecked the live app identity, desktop adapter, single receiver, HTTPS, rejection
of unsigned requests, and 27 passing local tests. No new event had arrived at that
snapshot. The subsequent user test on FARM-1186 verified both visible replies
against their completed Codex turns, actual FarmQA-authored Linear activities,
and separate `sent` records. Temporary prompt/final fields were cleared; the
session completed. This is transport/continuity coverage, not game interaction.

## Stop handling increment

User authorized the next cancellation increment on 2026-09-16. The deployed bridge
now handles authenticated Linear `agentActivity.signal: stop` events, durably
cancels queued work, suppresses pending ordinary replies, and records stop outcomes.
The installed app-tools 0.1.4 catalog has no active-turn interrupt tool. A possibly
running request stays `stop_pending` and blocks subsequent dispatch until its exact
turn is observed ending; FarmQA tells the operator to stop it manually in Codex.
Never treat reply suppression or a normal completion as successful interruption.
46 local tests and live-ledger-copy migration passed. Real Stop requests on
FARM-1186 and FARM-961 were acknowledged in 1.010 and 1.109 seconds. One queued
request never dispatched; both executed requests completed normally and their
ordinary final replies were suppressed. No interruption occurred. The FARM-961
error was visibly verified and accurately states the active-stop limitation.
Post-stop resume also passed on FARM-961 in 8.779 seconds, matching visible reply,
actual FarmQA activity, completed Codex turn, and `sent` ledger record. Manual
interruption had not yet been tested in that run. See
[evidence and limits](../reports/2026-09-16-farmqa-stop/report.md).

The later [manual Stop verification](../reports/2026-09-16-farmqa-manual-stop/report.md)
on FARM-961 ended the exact Codex waiting turn as `interrupted` after the user
clicked Stop. The ordinary Linear response was absent, and a newer follow-up
visibly returned `READY` in 12.914 seconds. This verifies the manual fallback,
not automatic interruption. PR #3 was subsequently merged by the user; this
later manual test did not change the deployed bridge code.

The [automatic Stop capability check](../reports/2026-09-16-farmqa-automatic-stop-capability/report.md)
found a documented `turn/interrupt` App Server method, but no supported
connection to the desktop-owned App Server or interrupt operation in the
installed app-tools connector. The exact inbox task is identifiable; a newly
started CLI App Server is not its running backend. Automatic interruption was
not deployed or live-tested. Retain the manual Stop gate and reply suppression.

## Session routing and pinned target increment

User approved separate conversations, one shared QA Unity/computer controller,
and durable target identity on 2026-09-16. The first implementation provides
one persistent Codex task mapping per new Linear session, FIFO dispatch within
a session, and an immutable selected-target snapshot per accepted message.
Existing sessions retain the legacy inbox. Separate tasks may process chat
concurrently; this grants no game/computer control.

Session routing is enabled on the Windows receiver using the saved FarmTestAgent
project. Task creation and initialization completion are tracked separately from
message dispatch. Uncertain creation is reconciled by a persisted input marker
without repeating creation. The shared inbox's three existing session mappings
and all 13 event states survived the migration check. 68 local tests pass. Fresh
sessions on FARM-1127 and FARM-1123 returned APPLE READY and PEAR READY through
distinct Codex tasks, matched against the Linear API, visible replies, and
delivery records. Both mappings survived a receiver restart. On 2026-09-17,
the same memory question returned APPLE on FARM-1127 and PEAR on FARM-1123
through their original tasks, matching the final records and Linear activities.

Live testing exposed two installed-app details: worktree tasks are omitted from
`list_threads`, and the creation prompt's first line is wrapped by `<input>`.
Regression fixes normalize the known delegation envelope and use a read-only
metadata-index fallback to discover candidate IDs. Binding still requires the
full random marker and completed initialization through the app's `read_thread`.

The 2026-09-17 follow-ups exposed empty `read_thread` item arrays despite
completed turns. A read-only rollout fallback now recovers only the exact
app-identified turns, verifies local task/turn/input/completion identities, and
keeps app status authoritative. It recovered the original waiting replies
without redispatch. 78 local tests pass. This depends on the installed local
record format and bounds each rollout read to 32 MiB; unavailable or ambiguous
records hold delivery for inspection. It does not establish a security boundary
between tasks or enable gameplay/automatic interruption.

Target selection is currently a local operator command using an existing client
ref/commit and a test-environment identifier. It neither changes checkouts nor
verifies the loaded Editor. No default client branch was invented. Automatic
branch/PR extraction, physical controller enforcement, and game-action cancellation
remain future increments. Reservation state and the inert worker are covered in
the later sections below. See [setup](../tools/README-farmqa.md),
[test procedure](../tests/scenarios/farmqa-sessions.md), and the
[deployment report](../reports/2026-09-16-farmqa-sessions/report.md).

## Controller reservation increment — 2026-09-17

The scheduling portion of the approved shared-controller design is implemented:
explicit operator enqueue of an authenticated event with a pinned target, one
durable FIFO reservation, and Stop propagation in the receiver transaction.
Queued Stop cancels immediately; active Stop retains ownership until the same
worker releases it. Restart cannot reclaim the slot. The queue does not execute
actions or enforce ownership on independently called Unity/computer tools.
93 local tests pass; a private live-ledger copy preserved all existing rows.
This is observed fixture/migration coverage, not live gameplay/cancellation.
Loaded Editor identity verification, physical worker enforcement, and bounded
action cancellation remain unimplemented. See the
[controller report](../reports/2026-09-17-farmqa-controller/report.md) and
[operator guide](../tools/README-farmqa-controller.md).

## Inert worker increment — 2026-09-17

The standalone inert worker now acquires one reservation, commits ownership,
waits for a bounded duration while polling cancellation, then releases after
the wait ends. Real subprocess fixtures verified signed Stop, other-session
Stop isolation, competing workers, actual wait duration, abrupt process death,
receiver restart, and database errors. Crashed/failed ownership stays held;
there is no automatic recovery or forced takeover. 104 local tests pass.
These are synthetic signed-event fixtures, not live Linear or Unity execution.
The existing receiver and live queue were left unchanged. See
[evidence and remaining gates](../reports/2026-09-17-farmqa-inert-worker/report.md).

## Read-only identity increment — 2026-09-17

Observed on Windows Unity 2022.3.62f3: a standalone per-request inspection now
records fresh Editor/project/platform metadata, Git commit/status/dirty hashes,
index metadata and loaded module IDs in the private ledger. It neither acquires
nor releases a reservation. Live verification used a private synthetic request,
not a production Linear message. Project, commit and build target matched;
four pre-existing dirty files were preserved; loaded-build provenance and game
server/session identity remain unknown. Overall result: **BLOCKED for gameplay**.

This supersedes the earlier statement that no identity checker exists, but does
not complete the actual-target gate. The utility always blocks; it never treats
Git or module IDs as proof of loaded code, or a requested environment as proof
of a connected session. It is not deployed as a worker/service or automatically
called by the bridge. Next: establish the trusted provenance and safe session
observation inputs, then physical action ownership/cancellation. See the
[report](../reports/2026-09-17-farmqa-identity/report.md) and
[operator guide](../tools/README-farmqa-identity.md).

## Provenance investigation — 2026-09-17

Observed at client `7dbf23bef80c660ceb5d384c2e99cff029e5b79a`, Windows Unity
2022.3.62f3: HotUpdate's loaded/disk module IDs and DLL/PDB debug identities
correspond. All 1,293 checked-in source documents match their compiled checksums
on disk and match Git after line-ending conversion. One generated source,
referenced binaries and full build inputs remain unverified. This narrows the
evidence gap but does not complete provenance or change the checker verdict.

Source-inferred session rules: require current authentication **and** transport,
stable auth generation and expected player. `LoginService` sets ZoneID to literal
1, so it cannot identify the environment. The loaded Net type exposes the named
state properties, but no authenticated live values were read in Edit Mode.

The subsequent user approval and execution supersede this investigation's
pending-build status; see the controlled-build entry below. No login or runtime
behavior change was made in the investigation.
Evidence and limits: [investigation report](../reports/2026-09-17-farmqa-provenance/report.md).

## Isolated controlled build — 2026-09-17

User-approved and observed: independently cloned client `7dbf23b` into the main
QA checkout's `.local/clients/farmqa-7dbf23b` and imported/compiled with Unity
2022.3.62f3 / StandaloneWindows64, Play Mode off. Original client dirty-file and
index hashes are unchanged. Fresh Console read: 0 errors, 550 warnings. Four
selected loaded module IDs match the new DLLs, and their DLL/PDB identities match.

BLOCKED for clean provenance: import changed `.vscode/settings.json` and
`Assets/Editor/SpineSettings.asset`; generated sources and full-project build
input coverage remain incomplete. Changes are preserved for investigation.
This does not enable gameplay, select an account/environment or change the
identity collector. Current Editor points to the isolated copy; rediscover it
before acting. Next: investigate the import drift and complete the evidence.
See [plan](../docs/farmqa-controlled-build.md) and
[execution evidence](../reports/2026-09-17-farmqa-controlled-build/report.md).

## Import drift investigation and recovery — 2026-09-17

Observed on the same isolated client/Unity target: the first-import stack enters
Spine's `GetOrCreateSettings` from an asset-save callback and calls CreateAsset
during import. The existing file was replaced with fallback shader/preset values.
Source-inferred cause: AssetDatabase could not yet load/find the checked-in
settings, and the package did not distinguish that from a missing file. Both
legacy EditorPrefs keys are currently absent. No machine preference was changed.

The exact pinned Spine settings were restored in the writable QA copy. Loaded
and cached settings match; two warm targeted reimports preserve them with zero
Console errors, Play Mode off and the original checkout unchanged. Only the
VS Code solution-name setting differs across 15,884 tracked inputs.

This supersedes the current-state Spine drift, not the historical build evidence.
Fresh-import prevention and previously imported asset correctness remain unknown;
gameplay and the positive identity gate stay disabled. Next: preserve the pinned
settings through a fresh import, validate affected assets and regenerate evidence.
See [report](../reports/2026-09-17-farmqa-import-drift/report.md) and
[regression scenario](../tests/scenarios/spine-import-drift.md).

Earlier operational state, 2026-09-17: the subsequent fresh-import attempt crashed
during the recovered Editor's project-switch shutdown. No fresh import ran;
Unity was closed at the last observation. Both original/recovered tracked states
were preserved. Fresh-import work is paused; do not automatically retry the
switch. See [failure report](../reports/2026-09-17-farmqa-fresh-import/report.md).
Subsequent user-authorized recovery reopened the recovered project visibly;
the original/recovered tracked states and pinned Spine settings remain unchanged.
MCP restart was initially pending. The user then enabled the existing Auto-Start
Server on Editor Load option. A direct launch automatically started and connected
MCP; fresh live verification passed with correct settings, four matching module
IDs, zero Console errors and Play Mode off. See
[recovery report](../reports/2026-09-17-farmqa-editor-recovery/report.md) and
[startup verification](../reports/2026-09-17-farmqa-mcp-autostart/report.md).
No new startup implementation was necessary; this option had been unset on
Windows. The user subsequently resumed the fresh-import test (below).


## Resumed fresh import — 2026-09-17

The user closed the recovered Editor normally; shutdown was clean. Direct visible
launch of the independent empty-Library `farmqa-fresh-7dbf23b` copy completed
import and automatically connected MCP. Spine settings preservation FAIL:
the same fallback shader/empty preset overwrite reproduced and is left intact.
The 169 atlas/170 material-texture structural rows match the recovered baseline,
with zero Console errors and four live/disk module matches. This is not rendering
or gameplay verification. Original and recovered checkouts are unchanged; the
fresh Editor remains open in Edit Mode. Complete provenance remains BLOCKED by
settings drift and missing generated-source evidence. See the updated
[fresh-import report](../reports/2026-09-17-farmqa-fresh-import/report.md).
