# FarmQA Linear integration

Last reviewed 2026-09-16. Load this for mention-service work, not gameplay rules.

| Claim | Prerequisites / evidence | Platform/build | Status / verified |
|---|---|---|---|
| Agent name is **FarmQA**, invoked as **@FarmQA**, with no space. First version sends any simple reply only. | Explicit user instruction in this session; see implementation report. | Platform-independent requirement | user-confirmed, 2026-09-16 |
| v0 handles signed created/prompted agent-session events and emits one fixed response. | `tools/linear_farmqa.py`; 12 local tests, mocked Linear API. | macOS arm64 / Python 3.13.14 / v0 working tree | observed locally, 2026-09-16; live routing unverified |
| Agent follow-up type is nested under `agentActivity.content.type`. | Linear SDK published `AgentActivityWebhookPayload`; corrected fixture failed before handler fix and passed afterward. | Developer API schema fetched 2026-09-16 | observed in schema and local replay, 2026-09-16 |
| Linear can supply a mentionable app identity and agent-session replies. | Official agents/API documentation linked in `tools/README-farmqa.md`. | Linear developer preview | inferred for this installation, 2026-09-16; live smoke pending |
| Workspace API settings showed no OAuth apps; private FarmQA creation form was prepared. | Browser state, Kuaiwa AI (`kuaiwagames`), 2026-09-16. | Linear web UI | observed, 2026-09-16; recheck before creation to avoid duplicates |

Use [setup and operations](../tools/README-farmqa.md) and the
[mention scenario](../tests/scenarios/farmqa-mention.md). Keep app credentials and
event DB in ignored `.local/farmqa/`; never put them in knowledge or reports.

User requested a PR before activation. [PR #1](https://github.com/Kuaiwa-Network/FarmTestAgent/pull/1)
contains the prototype on `codex/farmqa-hello` against `main`. The previously empty
remote was initialized with the existing QA baseline `903efc4`. Publication is
observed, 2026-09-16; merge and live activation remain pending.

Activation approval is pending. The browser tool requires confirmation for new
persistent app access. The form uses private distribution, client credentials,
only Agent session events, and a temporary HTTPS tunnel. The application has not
yet been created or authenticated. Do not tell users @FarmQA is live until the
app is installed and its identity is verified; do not claim reply success before
observing the actual Linear activity.

The earlier architecture discussion (shared identity, separate Editor/device
workers, exclusive instance/device/account ownership, human device priority,
queued full-suite jobs) is a proposal only. None of it is implemented in v0.

## Windows continuation, 2026-09-16

The earlier publication/merge status above is superseded: GitHub reported PR #1
already merged by `dunadain` at 08:03:01 UTC, commit `fc1e202`, and the source
branch deleted. This deployment session did not merge it. Fetching PR #1's head
confirmed the original `77cbcbc` tree matches main. Work continues on
`codex/farmqa-windows-deploy`.

Observed on Windows 11 x64 / Python 3.14.3: all 12 original tests pass. A direct
bind probe reproduced two simultaneous Windows listeners on one port; exclusive
binding fixes it, and all 13 tests pass. This remains mocked API evidence, not
proof of a live reply. The Windows account is not elevated. VisualSVN occupies
443; use the fresh temporary tunnel selected by the user and keep the receiver
on loopback. The app settings page, after user login, showed no OAuth apps.

See [the Windows report](../reports/2026-09-16-farmqa-windows/report.md) for current
activation state, process supervision, endpoint, evidence, and next steps.
Windows private storage requires NTFS ACLs; POSIX mode bits alone are insufficient.
