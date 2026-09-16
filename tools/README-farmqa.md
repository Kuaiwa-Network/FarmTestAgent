# FarmQA v0

One fixed response to a Linear agent mention or follow-up. Python 3.11+ standard
library only. No AI provider key, Codex invocation, game control, or suite queue.

Reply:

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
   0600. No access token is persisted. `--config PATH` selects another location.
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
   processes running and the Mac awake during the smoke test. This temporary
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
class are stored in `.local/farmqa/events.sqlite3`; prompt/issue content is not.

Pending events survive restart. Duplicate created events and duplicate prompted
activity IDs do not send twice. An API timeout, rejected mutation, or interrupted
send is `uncertain` and is not retried automatically. Inspect Linear before
attempting another mention. This intentionally avoids claiming exactly-once
delivery or treating an ambiguous network result as success. The service is for
a supervised low-volume test; do not run two copies against one database.

Stop the receiver and tunnel with Ctrl-C. Disable its webhook or revoke the
app's access from Linear when retiring the test. No client or server game code
is changed by this service.

## Authoritative API references

- [Linear agents](https://linear.app/developers/agents)
- [Agent session events and activities](https://linear.app/developers/agent-interaction)
- [Webhook authentication](https://linear.app/developers/webhooks)
- [Client credentials](https://linear.app/developers/oauth-2-0-authentication#client-credentials-tokens)
- [Application manifests](https://linear.app/developers/oauth-app-manifests)
- [Temporary tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)
