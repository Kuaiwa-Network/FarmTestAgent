# FarmQA Linear integration

Last reviewed 2026-09-16. Load this for mention-service work, not gameplay rules.

| Claim | Prerequisites / evidence | Platform/build | Status / verified |
|---|---|---|---|
| Agent name is **FarmQA**, invoked as **@FarmQA**, with no space; emits only the fixed connection reply. | Explicit user instruction; `tools/linear_farmqa.py`. | Platform-independent requirement | user-confirmed, 2026-09-16 |
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
commit. Windows work is in [draft PR #2](https://github.com/Kuaiwa-Network/FarmTestAgent/pull/2)
on `codex/farmqa-windows-deploy`. Keep it unmerged unless requested.

The live mention and follow-up both pass. Never infer delivery success from
HTTP 200 or `/health`. Uncertain send outcomes are
not automatically retried. Duplicate/restart delivery behavior is locally tested,
not established by a real Linear retry. No gameplay, issue creation, model calls,
workers, or suite scheduling are enabled, and no gameplay coverage is claimed.
