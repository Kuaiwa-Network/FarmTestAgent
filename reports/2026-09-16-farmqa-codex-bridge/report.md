# FarmQA forwarding to the Codex desktop app

Date: 2026-09-16. Host: existing Windows 11 deployment. Branch:
`codex/farmqa-windows-deploy`. No game checkout or game state changed.

## Scope and current state

The user explicitly requested forwarding FarmQA messages into a Codex app session.
This supersedes fixed-reply-only behavior for this deployment. No gameplay,
issue creation, game workers, game/client/server mutations, or suite scheduling
was authorized or enabled.

The receiver now runs in `codex` mode on `127.0.0.1:8765`, behind the existing
temporary HTTPS tunnel. It forwards to the visible desktop task **FarmQA Linear inbox**
(`01a0a9da-3777-7640-b19c-1aa1646ba210`), then posts that turn's final answer back
to the originating Linear agent session. All incoming sessions currently share
this one task and are handled serially. Task workspace:
`C:\Users\Mayn\.codex\worktrees\fde4\FarmTestAgent`.

## Observed evidence

- Local suite: 27 passing tests, including the original 13. External calls mocked
  in unit tests; real desktop transport tested separately below.
- The installed Codex CLI exposes `queue`, but its default app-server daemon
  socket connection failed. The desktop's running backend uses stdio. We did not
  expose an app-server port or launch a replacement model backend.
- The installed `codex-app-tools` 0.1.4 plugin exposes MCP stdio tools including
  `send_message_to_thread` and `read_thread`. A standalone local MCP client reached
  these using the app-provided pipe configuration.
- Task creation returned a pending client ID. The normal task listing omitted
  the created task; its real ID was recovered from the relevant desktop creation
  log and verified through `read_thread`. No duplicate task was created.
- First real adapter test: task received a prompt and returned
  `FarmQA desktop bridge received test one.`
- Second real adapter test: same task remembered that exact first reply and ran
  the documented `sky.list_apps()` discovery. It reported 40 app entries and
  three open windows. Tool execution succeeded. No app was opened or controlled.
- Desktop forwarding is represented by a `codex_app.send_message_to_thread`
  delegation output, not a `userMessage`, in this version. The matcher was fixed
  against that evidence and covered by a regression test. The app's read tool also
  enforces a 20,000-character item limit; the adapter uses that limit and permits
  final replies only up to 12,000 characters.
- Both scheduled tasks are running after the receiver restart; exactly one
  receiver listener binds loopback. Fresh startup verified the same FarmQA app and
  Kuaiwa AI workspace identity. Public HTTPS health returned 200 and an unsigned
  webhook returned 401. These do not prove a new live Linear round trip.

Live Linear bridge delivery: **PASS**. The user submitted an ordinary-comment
@FarmQA message on FARM-1188 and confirmed it worked. Linear reused the existing
agent session and delivered an `AgentSessionEvent` with action `prompted`.
The browser visibly showed the dynamic Codex answer; it exactly matched both
the completed desktop turn and the actual FarmQA-authored Linear response.
The SQLite record is `sent` with no error, 8.056 seconds from receipt to confirmed
reply. Its temporary prompt and response fields were cleared.

See [redacted live evidence](evidence/live-delivery.json). Codex turn:
`01a0a9f3-fca6-7ee0-b759-335d1cf4128c`; Linear activity:
`136d17fd-82f2-483f-91a0-d1436fc06362`. A brand-new `created` session and an
additional post-bridge follow-up have not been exercised live. The earlier
fixed-reply results and local desktop probes are not counted as those tests.

## Implementation and delivery behavior

`tools/linear_farmqa.py` keeps signature, timestamp, app/workspace validation and
the exclusive Windows socket. `mode: codex` opts into the bridge; otherwise the
original fixed reply is used. A separate table stores the minimal prompt payload,
acknowledgement ID, destination task, matched turn, and final response while pending.

The stages are acknowledgement → queue → dispatch → wait for matching final →
Linear response. The event marker correlates the exact forwarded message and
completed turn; idle status or unrelated final text cannot count as success.
Duplicate events do not dispatch twice. App availability/result reads can retry;
ambiguous dispatches and Linear writes cannot. Interrupted writes are marked
`uncertain`. Waiting for a result resumes with reads after receiver restart.
Prompt/final fields are cleared from active rows after confirmed delivery.

Configuration and SQLite backups remain inside ignored `.local/farmqa` under its
existing private NTFS ACL. Neither credentials nor full production prompts are
included in reports. The original ledger was backed up before switching modes.

## Limits and operations

- Supervised prototype; installed app-tools integration is version-dependent,
  not a published stable webhook API for Codex desktop.
- Codex app must run as the configured Windows user. A captured local pipe or
  installed runtime path may need rebinding after restarting/updating the app.
- Computer Use discovery passed through a forwarded turn. Actual application
  control and gameplay remain untested; Windows desktop must remain unlocked
  for future UI work, with required app permissions.
- One task shares context across FarmQA sessions. Avoid manual concurrent work in
  this inbox. No per-issue task isolation, attachments, live progress streaming,
  or dedicated Linear stop-signal cancellation is implemented.
- Prompts up to 32,000 characters, final replies up to 12,000 characters, and a
  15-minute result deadline. Missing/oversized content fails closed. A timeout
  can report an error without canceling a still-running Codex turn.
- The earlier quick-tunnel and current-user task limitations still apply. The
  public IP is not the ingress endpoint; tunnel restart may change the hostname.

See `tools/README-farmqa.md` for activation and rollback. Inspect the Codex task,
Linear activity, and matching ledger record before retrying an uncertain request.

## Remaining verification

The ordinary-comment mention passed through an existing session. To extend
coverage, exercise a genuinely new Linear agent session (`created`), then another
follow-up. Match the visible replies and turn/activity IDs as in the passed run.
Actual Computer Use interaction remains a separate, authorized test.
