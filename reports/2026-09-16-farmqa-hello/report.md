# FarmQA v0 implementation and verification

Date: 2026-09-16. Target: this QA repository, based on commit `903efc4`.
Platform: macOS arm64, Python 3.13.14. External target: Linear Kuaiwa AI workspace
(`kuaiwagames`). No Unity or Android runtime operated in this run.

## Scope and result

Implemented the user's narrowed request: exact identity **FarmQA** and one fixed
reply per mention/follow-up. No gameplay execution, bug creation, suite scheduling,
model invocation, or changes to game client/server/contract checkouts.

- **PASS (local)**: 12 automated tests, including loopback HTTP and mocked Linear
  token/mutation transport. Final observed run: 12 tests in 0.540s, exit 0.
- **PASS (preparation)**: official Cloudflare Tunnel 2026.9.1 downloaded to a
  temporary directory, release digest checked, quick tunnel connection registered.
  This is not proof that the webhook receiver is publicly ready.
- **BLOCKED (live activation)**: private app form prepared; confirmation requested
  because browser policy requires it before creating new persistent app access.
  No app/token created, no real webhook received, no Linear reply posted.
- **NOT TESTED**: real app permissions, mention menu appearance, live webhook
  delivery, live reply visibility, full gameplay or platform QA.

## Implementation

`tools/linear_farmqa.py` uses Python's standard library. The authenticated service
checks its FarmQA app identity, validates HMAC/timestamp and event identity,
durably accepts minimal event metadata, and sends `agentActivityCreate` with a
final response. Its local event ledger deduplicates mention/follow-up retries
across restart. Unknown send outcomes remain `uncertain`; no silent resend.

App setup requests `read,write,app:mentionable`. `write` is broader than the fixed
reply behavior. Narrower agent-activity permission support is unverified. Public
team access is the documented initial client-credentials behavior; restrict the
installed app to Farm when activating. No user connector token is reused.

## Verification evidence

See [trace](trace.jsonl), [local test results](evidence/local-tests.json), the
test cases in `tests/test_linear_farmqa.py`, and API references in the setup guide.
Local test results are synthetic; they do not represent Linear's production API.

The first 8 tests began with a missing implementation failure, then passed after
implementation. HTTP testing initially failed at socket bind under the sandbox;
the same test passed with approved loopback access. API schema review then found
that the first follow-up fixture incorrectly put type at the top level of the
activity. Correcting it to `content.type` reproduced an ignored prompt; the handler
was fixed and all 12 tests passed. No live message was affected.

Additional checks: `git diff --check` passed; CLI help and empty status worked.
The official archive's SHA-256 was
`c27ab8fd0aa489449e3d201eb02f957ef460a13b613662928b1b23394bf1bcfe`.
Tunnel binary SHA-256 reported
`9a0b19f67dc7a3011bc6b972c7ce06a5fcea8784ac6bd599ffa382ea4aeb5a6e`.

## State changes and limitations

Authored QA repository code/docs/tests; downloaded and started a temporary tunnel.
Prepared an unsaved Linear application form. No existing OAuth apps or webhooks
were changed. No credentials are present in tracked files. No client changes.

Temporary endpoint:
`https://layer-adjustments-times-flex.trycloudflare.com/webhook`.
It is run-specific and must be rediscovered if the tunnel restarts. At report
time the tunnel process is connected but the authenticated receiver is not
running. No permanent service or automatic restart has been installed.

## Lessons and next action

Verified procedure lesson: test webhook fixtures against the published schema,
not just prose or an inferred shape. The corrected follow-up test demonstrated
why passing mocks alone cannot establish integration correctness.

After activation approval: create the prepared FarmQA app, configure its client
ID/client secret/signing secret locally, authenticate and verify app/workspace
identity, restrict team access, start the receiver and verify public health.
Then ask the user to select FarmQA in an issue comment and run
`tests/scenarios/farmqa-mention.md`. Save actual session/activity evidence and
update this report. Until then the live connection remains unverified.

## PR publication, 2026-09-16

At the user's request, created [PR #1](https://github.com/Kuaiwa-Network/FarmTestAgent/pull/1):
`codex/farmqa-hello` → `main`. GitHub's repository was empty, so the existing local
QA baseline `903efc4` was published as `main` before the feature branch. No merge
or app activation was performed. A pattern scan of tracked files found no
credential literals or private-key/token patterns before publication.

Fresh validation: `python3 -m unittest discover -s tests -p 'test_*.py' -v`
passed all 12 tests in 0.534s, exit 0; `git diff --check 903efc4..HEAD` passed.
Independent read-only review found no blocking defects within the supervised
prototype scope. Live permissions and real mention/reply behavior remain untested.

## Windows continuation

See [the Windows deployment report](../2026-09-16-farmqa-windows/report.md).
It supersedes this report's historical merge status and Mac tunnel details.
PR #1 was already merged before the Windows session; that session performs no
merge. It uses newly inspected infrastructure and a fresh temporary tunnel.
