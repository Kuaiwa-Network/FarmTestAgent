# FarmQA Linear receiver

Python 3.11+ standard-library receiver with two modes. The default `fixed` mode
sends one connection-test response. The optional `codex` mode forwards messages
to a dedicated task in the running Codex desktop app and returns its final answer.
That mode also needs the app's installed Node runtime and app-tools MCP plugin.
No separate OpenAI API key, game control, or suite queue is configured.

Default-mode reply:

> FarmQA is connected 🌱 I received your message. This is a connection test;
> gameplay testing is not enabled yet.

## Set up once

1. In Linear Settings → API, create a **private** OAuth application named exactly
   **FarmQA**, developer Kuaiwa. Enable **Client credentials**, **Webhooks**, and
   only **Agent session events**. Register a loopback redirect URI such as
   `http://127.0.0.1:8765/oauth/callback` (required by the app form; v0 uses client
   credentials, so it does not implement or use that callback).
2. Point its webhook at the HTTPS tunnel URL plus `/webhook`.
3. Configure locally; do not paste secrets into a chat or tracked file:

   ```sh
   python3 tools/linear_farmqa.py configure
   ```

   This prompts for client ID and hides the client secret and webhook signing
   secret. The resulting `.local/farmqa/config.json` is ignored by Git and mode
   0600 on POSIX. On Windows, restrict the parent directory's NTFS ACL before
   configuring; `chmod(0600)` does not establish a private Windows ACL. No access
   token is persisted. `--config PATH` selects another location.
4. Start the receiver:

   ```sh
   python3 tools/linear_farmqa.py serve
   ```

   It obtains an app token using `read,write,app:mentionable`, verifies the API
   viewer name is FarmQA, records its app/workspace IDs, and binds
   `127.0.0.1:8765`. `write` is broader than this bot's behavior. No issue-creation,
   assignment, or admin scopes are requested. Validate permissions in the first
   live test; narrower agent-activity permissions have not been established.
5. Run a temporary tunnel in a second terminal:

   ```sh
   cloudflared tunnel --url http://127.0.0.1:8765 --no-autoupdate --protocol http2
   ```

   Update Linear's webhook URL if the quick-tunnel hostname changes. Keep both
   processes running and the computer awake during the smoke test. This temporary
   endpoint is not an unattended hosting solution.
6. Mention **FarmQA** by selecting it from Linear's `@` menu in a comment. Text
   that merely looks like `@FarmQA` without selecting the app may not invoke it.
   Expect the fixed message in its agent session, then a completed session.

The administrator controls team access in the installed application settings.
Client-credentials tokens initially access public teams in the owning workspace;
restrict access to the Farm team when activating this internal agent.

## Verify and inspect

```sh
python3 -m unittest discover -s tests -p 'test_linear_farmqa.py' -v
python3 tools/linear_farmqa.py status
curl http://127.0.0.1:8765/health
```

The HTTP test needs permission to bind an ephemeral loopback port. It mocks the
external Linear API and cannot prove real mention routing or OAuth permissions.
`/health` means receiver ready, not proof of a successful reply. Inspect the
Linear activity and matching `sent` record for a real delivery.

Webhook validation checks raw-byte HMAC-SHA256, timestamp within 60 seconds,
client/app/workspace identity, event type and action. HTTP 200 means durable
acceptance; it is not the final delivery result. IDs, status, times and exception
class are stored in `.local/farmqa/events.sqlite3`. Fixed mode stores no prompt
content. Codex mode temporarily stores the minimal forwarded context and response
in the private ledger; it clears those fields after confirmed delivery.

Pending events survive restart. Duplicate created events and duplicate prompted
activity IDs do not send twice. An API timeout, rejected mutation, or interrupted
send is `uncertain` and is not retried automatically. Inspect Linear before
attempting another mention. This intentionally avoids claiming exactly-once
delivery or treating an ambiguous network result as success. The service is for
a supervised low-volume test; do not run two copies against one database.

Stop the receiver and tunnel with Ctrl-C. Disable its webhook or revoke the
app's access from Linear when retiring the test. No client or server game code
is changed by this service.

## Windows connection-test deployment

See [the Windows run report](../reports/2026-09-16-farmqa-windows/report.md)
for this machine's actual endpoint, service status, and live verification.
The receiver remains on `127.0.0.1:8765`. VisualSVN owns port 443 on this host;
the connection test uses a fresh Cloudflare quick tunnel without changing SVN,
router forwarding, or firewall policy. A quick tunnel hostname changes when its
process restarts, so update the Linear app webhook URL before another live test.

Before `python3 tools/linear_farmqa.py configure`, prepare private local storage
from the repository root in PowerShell:

```powershell
New-Item -ItemType Directory -Force .local/farmqa/bin,.local/farmqa/logs | Out-Null
$farmqaSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
icacls.exe .local/farmqa /inheritance:r /grant:r ("*$($farmqaSid):(OI)(CI)F") '*S-1-5-18:(OI)(CI)F'
python3 tools/linear_farmqa.py configure
```

Install `cloudflared.exe` from the official Cloudflare release into
`.local/farmqa/bin/`, checking its SHA-256 against the official release asset's
digest. The runtime Python program still uses only the standard library.

`farmqa-windows-supervisor.ps1` runs either `receiver` or `tunnel` hidden, restarts
its child after 10 seconds, and takes a file lock to prevent two supervisors for
the same component. It keeps child PID files and the latest launch's stdout/stderr
under the private local directory. It can adopt an existing child with a matching
executable path, arguments, and PID. Only this deployment's PID files belong there.

Create two current-user scheduled tasks named `FarmQA-Receiver` and
`FarmQA-Tunnel`, with an at-logon trigger, `Interactive` logon, `Limited` run
level, `IgnoreNew` multiple-instance policy, no execution time limit, and restart
on failure (one minute, three attempts). Use an installed PowerShell host whose
policy permits these local scripts. Pass absolute paths to the supervisor and
Python executable. Do not change execution policy globally. Example action:

```text
pwsh.exe -NoProfile -WindowStyle Hidden -File "<repo>\tools\farmqa-windows-supervisor.ps1" -Component receiver -Python "<absolute-python.exe>"
pwsh.exe -NoProfile -WindowStyle Hidden -File "<repo>\tools\farmqa-windows-supervisor.ps1" -Component tunnel
```

These tasks run while that Windows user is logged in. They are appropriate for
this supervised connection test, not unattended boot-time hosting. Keep the PC
awake. A permanent endpoint and boot-time service are separate future work.

```powershell
Get-ScheduledTask FarmQA-Receiver,FarmQA-Tunnel
Get-Content .local/farmqa/logs/receiver.stdout.log
python3 tools/linear_farmqa.py status
Select-String -Path .local/farmqa/logs/tunnel.stderr.log -Pattern 'https://[-a-z]+\.trycloudflare\.com'
```

To stop: disable and stop both scheduled tasks, then stop only their verified
child PIDs (check executable path against this deployment before `Stop-Process`).
Stopping the task alone may leave a child running. Never delete the SQLite ledger
to resolve an uncertain send; inspect Linear first. Do not start another receiver
using the same database on a different port.

## Codex desktop forwarding

See [the bridge report](../reports/2026-09-16-farmqa-codex-bridge/report.md) for this
machine's destination and verification. This uses the installed app-tools MCP
plugin to call `send_message_to_thread` and `read_thread`. It does not launch
`codex exec`, expose app-server to the network, or automate the Codex UI.
The integration depends on the installed plugin version and an app-provided local
pipe; treat it as a supervised prototype, not a stable public Codex desktop API.

1. Create a dedicated **local Codex app task**, inspect its tools, and record its
   real task ID. Keep one inbox for this prototype. Do not use a pending client ID.
2. From a Codex app command tool (which provides the app-tools environment), run:

   ```powershell
   python3 tools/farmqa_codex.py configure --thread-id <task-id> --server-path <installed-codex-app-tools-server.mjs>
   python3 tools/farmqa_codex.py check
   ```

   This saves `.local/farmqa/codex.json` privately. Do not paste its contents into
   chat or Git. Keep the existing restrictive Windows directory ACL. The app must
   stay running. After an app restart, use `python3 tools/farmqa_codex.py rebind`
   from an app command tool; pass a new `--server-path` if the plugin was updated.
   Restart the receiver afterward so it reloads the binding.
3. With no events in flight, make a private SQLite backup, then add
   `"mode": "codex"` to `.local/farmqa/config.json` without replacing credentials.
   Stop the receiver supervisor, wait until it has stopped and released its lock,
   stop only its verified child PID, then restart the receiver task. An immediate
   stop/start can race the old file lock; verify both task state and the listener.
   Leave the tunnel running so its hostname remains unchanged.
4. Verify startup identity, one listener on loopback, HTTPS, and rejected unsigned
   webhooks. Send a real @FarmQA mention and follow-up. Match each Codex turn's
   final text and Linear activity ID against the ledger; health alone is insufficient.

The receiver acknowledges new events, queues them, dispatches one request at a
time, reads the matching completed Codex turn, and returns the final answer through
`agentActivityCreate`. The task uses its configured model and permissions. A
forwarded message does not independently grant app-control permissions.
No tools' intermediate output or reasoning is posted to Linear.

`python3 tools/linear_farmqa.py status` omits prompt/response content. For pending
bridge records, inspect `bridge_jobs` using an explicit metadata-only projection
(`event_key, thread_id, turn_id, next_check, deadline`). Never dump the table into
logs because it contains temporary message content. Run all relevant tests with:

```powershell
python3 -m unittest discover -s tests -p 'test_*farmqa*.py' -v
```

An ambiguous dispatch or final-send timeout is `uncertain` and will not resend.
Read-only availability/result polling can retry. The result deadline is 15 minutes;
timing out does not cancel an already-running Codex task. Inputs are limited to
32,000 characters and final answers to 12,000 characters. One inbox shares context
across issues; avoid manually starting concurrent work there. Attachments, progress
streaming, per-issue task isolation, and Linear stop-signal cancellation are not
implemented. App clicking and gameplay require their own authorized verification.

Rollback: stop accepting new work, inspect/resolve pending or uncertain bridge
records, change `mode` back to `fixed`, and restart only the receiver. Keep both
ledgers and the original backup; do not erase them to force retries.

## Authoritative API references

- [Linear agents](https://linear.app/developers/agents)
- [Agent session events and activities](https://linear.app/developers/agent-interaction)
- [Webhook authentication](https://linear.app/developers/webhooks)
- [Client credentials](https://linear.app/developers/oauth-2-0-authentication#client-credentials-tokens)
- [Application manifests](https://linear.app/developers/oauth-app-manifests)
- [Temporary tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)
