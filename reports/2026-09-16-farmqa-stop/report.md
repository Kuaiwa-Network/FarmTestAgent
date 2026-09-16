# FarmQA Stop handling — 2026-09-16

Outcome: queued cancellation and ordinary-reply suppression implemented and
deployed. **Automatic interruption of active Codex work remains BLOCKED.**
The installed desktop connector does not expose that operation. No gameplay or
exclusive game-controller implementation is included in this change.

## Evidence and implementation

The real installed `codex-app-tools` 0.1.4 MCP catalog exposes 38 tools and zero
stop/cancel/interrupt task tools. Source inspection distinguishes cancellation
of a pending MCP tool call from interruption of the Codex turn it already
dispatched. The CLI exposes an App Server protocol, but the current bridge is
connected to the desktop app-tools pipe, not a control transport to that backend.
No alternate backend, public control port, process kill, app handoff, or Codex UI
automation was substituted for a supported interrupt operation.

[Linear's documented stop signal](https://linear.app/developers/agent-signals)
is handled under `agentActivity.signal` on a prompted activity. It is checked
after authentication and identity validation and before extracting message text.
The receiver stores a deduplicated control record and an authored-time cutoff,
marks affected jobs, and clears their temporary input/final content. Older delayed
events cannot restart stopped work; a newer authored prompt can resume after the
earlier execution has ended. Missing authored times after a stop fail closed.

Queued work is cancelled without dispatch. An already dispatched job keeps the
single-inbox queue held as `stop_pending`, and its normal final reply is suppressed.
FarmQA posts a clear error telling the user that active execution is not confirmed
stopped and must be stopped in the Codex inbox. Read-only checks correlate the
exact event-marked turn and record its actual terminal status. A task that finishes
normally after Stop is recorded as `completed`, never as interrupted. No missing
turn or idle-only observation can release the hold.

[OpenAI's App Server documentation](https://learn.chatgpt.com/docs/app-server)
defines `turn/interrupt` and an eventual `interrupted` status, but it does not
establish availability through this machine's installed desktop tool connector.
A supported connection to the actual desktop backend is still needed for full
automatic interruption. No such connection is claimed by this increment.

Outgoing Linear calls that started before a stop cannot be recalled. Confirmed
or ambiguous in-flight delivery is recorded explicitly and never blindly retried.
Stopping does not undo any already completed tool or game action.

## Validation

- **46 local tests passed**, including the original transport/security tests and
  new stop races, restart, ordering, scope, result correlation, and ambiguity checks.
  External Linear/desktop calls are mocked in these tests.
- A private backup was taken. Migration was tested on a copy of the real ledger:
  all seven historical event rows remained unchanged, three bridge records were
  preserved, and SQLite integrity passed. The first probe's Windows cleanup failed
  because a backup connection was not closed; the corrected probe explicitly
  closed connections and passed. The live DB was not modified by that failed probe.
- Receiver restarted while the inbox was idle and no delivery was in flight.
  Exactly one listener remains at `127.0.0.1:8765`, PID 8848. Both scheduled tasks
  are running. The existing tunnel was not restarted.
- Startup identity is still FarmQA / Kuaiwa AI, desktop adapter is reachable, public
  HTTPS health is 200, and an unsigned webhook is rejected with 401.
- **Real Linear Stop, manual interruption, and post-stop resume: pending.** The user
  has been asked to run the harmless 60-second wait scenario on FARM-1186. Neither
  local test results nor service health are counted as that live test.

See [local tests](evidence/local-tests.txt), [migration/capabilities](evidence/predeployment.json),
and [deployment](evidence/deployment.json). Credentials and message bodies remain
outside tracked evidence. Existing client changes and the inbox checkout are unchanged.

## Next steps and limits

1. Observe the user's Linear stop test and record the actual terminal outcome,
   suppressed ordinary final, visible stop reply, and a newer follow-up.
2. Obtain a supported active-turn interrupt capability and verify interruption
   end to end before enabling gameplay. The currently deployed fallback is manual.
3. Establish one controller per game instance, target/build and safe test-session
   identity before the existing bounded one-plot scenario.

The temporary HTTPS hostname, logged-in Windows user, and running desktop app
remain required. Reports/knowledge from the prior fresh-session verification are
included on this continuation branch. PR #2 was already merged by the user; no
merge was performed here.
