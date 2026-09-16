# FarmQA mention smoke test

User-approved scope: implement **FarmQA** (no space), responding with one fixed
message. This narrows the previously discussed Linear bridge. No model invocation,
gameplay, bug creation, suite scheduling, or Editor/device queue in this increment.

## Design

- Private Linear OAuth app, app identity, mentionable. Subscribe only to
  `AgentSessionEvent`. Use the documented client-credentials grant for this
  single-workspace development service; never reuse the user's connector token.
- Python standard-library HTTP receiver on loopback, temporarily reachable by
  HTTPS tunnel for the supervised smoke test. Only health and signed webhook routes.
- Verify HMAC over raw bytes, recent timestamp, app and workspace identity.
- Persist minimal event IDs and result in SQLite before returning HTTP 200. A
  worker emits a single final `response` activity immediately. No need for an
  intermediate thought for this constant-time reply.
- Deduplicate by session creation / prompted activity ID, including across restart.
  Persist the outbound activity ID before sending. Ambiguous failures remain
  visible and are not automatically retried, to avoid duplicate messages.
- Do not log prompts, issue bodies, tokens, secrets, or raw webhook payloads.
- Fixed reply: “FarmQA is connected 🌱 I received your message. This is a
  connection test; gameplay testing is not enabled yet.”

## Implementation and verification

1. Write failing tests for authenticated events, forged/stale/wrong-app rejection,
   duplicate delivery, follow-up prompts, failed sends, and restart behavior.
2. Implement receiver, durable minimal inbox, Linear API client and start/configure
   commands; run tests. Add a real local HTTP test with mocked external Linear API.
3. Prepare a private FarmQA app and HTTPS webhook; keep credentials ignored and
   mode 0600. Verify app identity before listening. Review requested scopes during
   registration; agent-activity scope requirements need live verification.
4. Let the user mention FarmQA on their chosen issue. Verify actual activity delivery
   and record a redacted trace. Until this happens, live integration is unverified.
5. Save operating instructions, results and exact remaining setup if any; commit.

## Sources checked 2026-09-16

- https://linear.app/developers/agents
- https://linear.app/developers/agent-interaction
- https://linear.app/developers/webhooks
- https://linear.app/developers/oauth-2-0-authentication
- https://linear.app/developers/oauth-app-manifests
- https://raw.githubusercontent.com/linear/linear/refs/heads/master/packages/sdk/src/schema.graphql

Self-review: this is a temporary development service, not a production hosting
solution. The tunnel and service must stay running; restart must not resend a
possibly completed mutation. Tests cannot establish actual Linear permissions or
mention routing; those require the user-triggered live smoke test.
