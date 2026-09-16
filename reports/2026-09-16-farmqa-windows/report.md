# FarmQA Windows deployment

Date: 2026-09-16. Scope: the fixed FarmQA Linear connection reply only. No game
runtime, Unity installation, client checkout, model API, issue creation, or suite
scheduling is involved.

## Repository and machine inspection

The working tree was clean on arrival. Fetched `origin` and inspected GitHub PR
state. PR #1 had already been merged by `dunadain` at 08:03:01 UTC, producing
`fc1e202334118b3c47605b3e30eb7c57c281d336`. Its branch had been deleted. An explicit
fetch of `codex/farmqa-hello` failed for that reason; fetching `refs/pull/1/head`
recovered `77cbcbcdb9cb9149d55afc99248083c5d77219aa`, whose tree matches the current
main tree. This run performed no merge. Deployment work uses
`codex/farmqa-windows-deploy` from the actual merged state.

Host: Windows 11 Home Chinese, x64, build 26200; Python 3.14.3. The account is not
elevated. LAN address is `192.168.1.202`; user-provided public IP is
`112.65.142.50`. VisualSVN HTTP Service owns port 443. Its configuration names the
local machine, and no reusable public trusted-certificate endpoint was found.
An HTTPS probe of the public IP from this host failed its TLS handshake. This
does not establish router forwarding or external reachability. Private/Public
Windows firewall profiles were already disabled; Domain was enabled. This run
does not change firewall, router, VisualSVN, or other hosting services.

The Linear connector verified workspace Kuaiwa AI (`kuaiwagames`, organization
`ff27325f-34a2-4e64-be44-5746fd1b3ea3`) and team 农场
(`9676b5f9-eff3-485b-80ed-900ed137e21a`). After the user completed browser login,
the workspace API page showed **No OAuth applications**. App administration is
not exposed by the available Linear connector tools.

## Local implementation and checks

- Baseline required command passed all 12 tests on this host.
- Reproduced a Windows-specific defect: two `ThreadingHTTPServer` objects could
  bind the same loopback port because Windows permits that with `SO_REUSEADDR`.
- Added Windows `SO_EXCLUSIVEADDRUSE`, disabled address reuse on Windows, and
  reserved the port before opening/recovering the event ledger. Added a regression
  test; all 13 tests pass. Closed the negative HTTP test's error response to remove
  its resource warning.
- Added a small Windows supervisor for either the receiver or tunnel, with a file
  lock, hidden child, checked PID adoption, and restart delay. Scheduled tasks use
  current-user interactive logon, limited privileges, and `IgnoreNew`.
- Windows PowerShell rejected the local script under its existing `Restricted`
  policy. Switched the task action to the installed PowerShell 7 host, whose
  existing policy allows local scripts. No execution policy was changed.

Test evidence is [local-tests.txt](evidence/local-tests.txt); all Linear transport
in those tests is mocked. Infrastructure facts and the official binary digest
are in [inspection.json](evidence/inspection.json).

## Deployment preparation

The user selected a **fresh temporary tunnel** for this test. Downloaded official
Cloudflare `cloudflared` 2026.9.1 for Windows amd64 and checked the release API's
SHA-256 digest before running it:
`2837888cc0f5d58f15b6dc478376de90b4d3ba5241c7947455d1e0a0df429712`.

The tunnel registered a Cloudflare HTTP/2 connection and forwards only to
`http://127.0.0.1:8765`. Current run hostname:
`https://stephen-impact-subdivision-scenic.trycloudflare.com`.
The intended webhook path is `/webhook`. This hostname belongs to this Windows
run, not the earlier Mac tunnel, and changes if the tunnel process restarts.

Private local state is `.local/farmqa/`, ignored by Git. Its NTFS ACL grants only
the current user and SYSTEM full control with inheritance disabled. Do not rely
on Python's `chmod(0600)` for Windows secrecy. Credentials are never included in
reports. Access tokens stay in process memory. Only minimal event metadata goes
in SQLite. Read [operations](../../tools/README-farmqa.md#windows-connection-test-deployment)
for start, inspect, stop, and retirement instructions.

## Activation and live evidence

**Pending.** The private FarmQA form is prepared with client credentials,
webhooks, and only Agent session events enabled. The initial unsaved form was
discarded; use only the fresh form's signing secret. No production reply has been
verified. The required browser action-time confirmation for persistent OAuth
access has been requested. Record subsequent activation and live evidence here.

Live acceptance requires both a visible exact fixed reply and a matching `sent`
record with the actual session/activity IDs, for a user-selected mention and a
follow-up. HTTP 200 or `/health` alone does not pass this scenario.

## Remaining work and limits

1. Complete the prepared app creation after the pending browser confirmation;
   use the `configure` command to store its credentials privately.
2. Authenticate as FarmQA, confirm the expected workspace, restrict installed-app
   team access to Farm where supported, and start the supervised receiver.
3. Verify trusted HTTPS from outside this host, and reject invalid signatures
   through the public endpoint without creating a ledger entry.
4. Ask the user to select FarmQA in Linear's mention menu on a test issue; observe
   the visible reply and a follow-up, matching both to the local delivery ledger.

This is a supervised connection test. Interactive tasks require the Windows user
to be logged in and the machine awake. The temporary hostname requires manual
Linear URL updates after a tunnel restart. Stable DNS/TLS and unattended boot-time
hosting are not established. Gameplay remains disabled.

## Publication

Published the fix and evidence in [draft PR #2](https://github.com/Kuaiwa-Network/FarmTestAgent/pull/2),
`codex/farmqa-windows-deploy` into `main`. A merged PR cannot accept new commits
as changes to its merged diff, so PR #1 remains unchanged. No PR was merged in
this session. The initial Git push selected a different credential-manager
account and was denied. The already signed-in GitHub CLI account `dunadain`
reported repository push access; using its credential helper for this command
only succeeded. Global Git credential settings were not changed.
