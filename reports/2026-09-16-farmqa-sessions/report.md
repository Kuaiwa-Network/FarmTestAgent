# FarmQA session routing and target snapshots — 2026-09-16

Outcome: **PASS for local tests, deployment, and two independent live initial
replies; follow-up isolation PENDING.** Gameplay remains disabled. This is the first increment of
the user's approved conversation/queue/controller design.

## Implemented behavior

Each newly seen Linear agent session can create a separate Codex app task in a
worktree of the saved FarmTestAgent project. Existing sessions retain their
original task and queued destinations. The SQLite ledger stores the mapping,
creation state, and a random binding marker before any task-creation call.
An uncertain creation is not repeated; the bridge performs bounded read-only
reconciliation. A pending worktree `clientThreadId` is never used as an actual
task ID. The initialization turn must complete before a user message is sent.

Messages are dispatched in acceptance order per session. Different isolated
tasks may process chat concurrently. Stop affects only its originating session;
new requests to the same task wait for the exact stopped turn to end. The
manual Stop instruction names the actual task ID. Legacy sessions still share
their original inbox and serialize access to it.

A local operator can pin an existing full client Git ref or commit and a test
environment identifier. Resolution only reads Git. Every new message copies
the selected target into its own durable snapshot; changing the session's
selection or advancing the branch cannot retarget an already queued message.
An unspecified target remains null. The record explicitly says that it is not
verified against the running Unity build.

## Validation and deployment

Source implementation: commits `11db127` and `cbdc5c9` on `codex/farmqa-session-routing`, based
on `main` `df2b48d` plus the earlier capability report. Python standard library
only, Windows 11, Python 3.14.3. No client/server/game checkout was changed.

- 68 local tests passed: the prior 46 plus 22 routing/target tests. New coverage
  includes independent replies from two sessions on the same issue, follow-ups
  across restart, FIFO under delayed polling, unknown/pending creation, Stop
  races during provisioning, Stop isolation, legacy migration, duplicate binding
  rejection, initialization completion, target snapshots after branch movement,
  and routing configuration retention during rebind. External app/Linear writes
  were mocked; real Git operations used disposable fixture repositories.
  Two further regressions cover the observed delegation envelope and read-only
  metadata recovery for worktree tasks omitted from the app's task list.
- A private copy of the live ledger preserved all 13 event keys/states and
  destinations through migration and produced three legacy session mappings.
  Private pre-deployment database and Codex-config backups were retained under
  ignored `.local/farmqa/backups/`. No active events were present at preflight.
- The installed app-tools catalog was read directly. The configured QA project
  was verified by ID/path as a local Git repository; worktree creation was
  selected. The existing inbox was idle. No test tasks were created by the
  preflight itself.
- Session routing was enabled and only the receiver was restarted. Its startup
  identity remained **FarmQA** in **Kuaiwa AI**. Final process inspection found
  one receiver and one supervisor, with one listener on `127.0.0.1:8765`.
  The tunnel was left running, preserving its webhook address.
- During restart, an immediate supervisor-lock probe encountered a still-held
  lock. Final process/listener/schema checks established one receiver and one
  supervisor with the new schema/config active; this was not treated as a
  successful lock probe. Future restart scripts should wait for actual lock
  release and use terminating errors, rather than relying only on task state.
- Loopback and the existing public HTTPS hostname returned health 200 and
  rejected unsigned webhooks with 401. TLS validation used Python's default
  trusted-certificate checks. These requests originated on this machine. The
  separate web-fetch service refused the public URL as unsafe to open, so no
  independent diagnostic result from that service is claimed. The subsequent
  real authenticated Linear webhooks below verify external inbound delivery.

## Live initial replies and integration fixes

The user's new mentions created two actual Codex worktree tasks, but the bridge
initially held both messages in `TaskSetupPending`. Inspection showed that the
installed app's `list_threads` omits these tasks (their local `project_id` is
null), and its `create_thread` delegation envelope places the binding marker
directly after `<input>` instead of on a standalone line.

The fix normalizes the known delegation envelope and adds a bounded read-only
metadata lookup by the generated task name when the app listing has no candidate.
This lookup reads IDs only from the configured local `state_5.sqlite`; the app's
`read_thread` must still verify the actual task ID, full random input marker,
and completed initialization. The index is not modified, and no task creation
was repeated. Both fixes have regression tests. After deploying the fix, the
original queued messages were delivered exactly once.

| Issue | Actual Codex task | Visible and API-verified reply |
|---|---|---|
| FARM-1127 | `01a0aa97-0d34-7813-a18a-7ec38763d76d` | `APPLE READY` |
| FARM-1123 | `01a0aa97-6f60-7d21-8f35-1d3c38296de1` | `PEAR READY` |

Both final texts matched the exact event-marked Codex turn, FarmQA-authored
Linear activity in the originating issue/session, and `sent` ledger record.
Both appeared in the Linear agent chat UI. Transient prompt/final fields were
cleared. Total receipt-to-delivery times were 310.029 and 291.138 seconds,
including investigation and deployment of the discovery fix; these are not
normal-latency measurements. See [allowlisted evidence](evidence/live-sessions.json).

The receiver was restarted again after both jobs completed. Its two mappings
survived unchanged and remained `ready`. The user was asked to send the same
memory question in both chats to verify live follow-up continuity and isolation.

## Remaining verification and limitations

Initial replies are verified. Next verify a follow-up and per-session Stop using the
[session scenario](../../tests/scenarios/farmqa-sessions.md).

Task creation recovery can remain held if the task is renamed, the installed
metadata schema changes, its initial input falls outside the latest 10 turns,
or multiple candidates match. The read-only index fallback is an additional
machine-specific dependency, not a stable public API. Do not reset creation
state or retry blindly.

Natural-language branch/PR resolution, a default client branch, account/server
version verification, the exclusive physical controller, persisted observed
Unity identity, and game-action cancellation are not implemented here. Automatic
interruption of Codex itself remains unavailable. Chat-task instructions still
prohibit gameplay; they are not a machine-enforced controller lock. Live gameplay
must stay disabled until the controller increment is implemented and verified.

Operational commands, target selection, and rollback are documented in
[tools/README-farmqa.md](../../tools/README-farmqa.md). Changes are committed
locally; no PR was pushed or merged during this increment.
