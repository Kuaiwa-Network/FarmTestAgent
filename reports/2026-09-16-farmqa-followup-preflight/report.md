# FarmQA follow-up verification and Windows readiness

Date: 2026-09-16. Scope: recheck the deployed bridge, verify a genuinely new
Linear session and follow-up, and inspect gameplay prerequisites. No gameplay ran.

## Live result: PASS

The user completed both messages on [FARM-1186](https://linear.app/kuaiwagames/issue/FARM-1186).
Linear created a new agent session, `0b81363f-bb0c-4238-8f9a-b1f85cef99c3`.
The initial `created` event and subsequent `prompted` event each produced the
visible reply `fresh bridge test passed`. The follow-up asked for the exact
previous phrase, confirming continuity through the same dedicated Codex task.

| Event | Receipt to confirmed delivery | Codex turn | Linear response activity |
|---|---|---|---|
| `created` | 11.460 s | `01a0aa1b-95a6-7792-9c01-1ec370202dc3` | `0857835e-74d0-43ca-9f29-12540cdc05f0` |
| `prompted` | 8.137 s | `01a0aa1b-e4bd-7bc0-a5e2-1fa9a0664d85` | `3285e1a1-6e00-495b-a6eb-912bc6b7ee5a` |

Both visible browser replies exactly matched the actual FarmQA-authored Linear
activities and completed Codex final answers. Both ledger rows are `sent`, with
no error and cleared temporary input/response fields. The Linear session is
`complete`. See [redacted live evidence](evidence/live-delivery.json).
This verifies message transport and conversation continuity, not gameplay or
unattended reliability. No integration code change was necessary.

## Bridge preflight

- All 27 local tests passed. External Linear and desktop calls remain mocked in
  the unit suite; these tests do not replace a live mention.
- `FarmQA-Receiver` and `FarmQA-Tunnel` were both running. Exactly one receiver
  listened on `127.0.0.1:8765` (PID 31348).
- The existing trusted HTTPS endpoint returned health 200 and unsigned webhook
  401. No receiver, tunnel, firewall, or credential change was needed.
- Fresh API identity matched FarmQA and the Kuaiwa AI workspace. The desktop
  adapter reached the idle **FarmQA Linear inbox** task.
- The five historical delivery records remained `sent`. No new event had arrived
  after the previously verified Codex round trip when this snapshot was saved.

The user was asked to select @FarmQA on an existing Farm test issue that has never
used it, request `Reply exactly: fresh bridge test passed`, then ask in that agent
chat `What exact phrase did you just reply with?` and provide the issue link.
That test was pending at the preflight snapshot and is now **PASS**, as recorded
above. The earlier repeated mention on FARM-1188 reused its existing session;
FARM-1186 supplies the separate real `created`-path evidence.

See [bridge evidence](evidence/bridge.json). Prompt bodies, response bodies, and
credentials are excluded from this snapshot.

## Gameplay readiness

The installed Editor at `D:\Program\UnityEditor\2022.3.62f3\Editor\Unity.exe`
reports `2022.3.62f3_96770f904ca7`, matching the project's declared version. No
Unity Editor process was running; Unity Hub alone does not establish readiness.

The actual local client is `D:\AgentWorkSpace\Farm\Farm-Client`, revision
`7dbf23bef80c660ceb5d384c2e99cff029e5b79a`. It has three modified device-MCP files
and one untracked compiler test. Their hashes are recorded and all were preserved.
The checkout was not fetched, updated, built, or edited. Its on-disk HotUpdate DLL
does not establish any currently loaded game's identity.

ADB enumeration returned no devices. A separate existing Farm device broker was
already listening on `127.0.0.1:8973` (PID 21904). Its ownership and agent registry
were not established; it was left running and no second broker was launched.
The client declares the Coplay Unity MCP package, but this task currently exposes
no Unity/device MCP tools. Package presence is not a successful Editor connection.

The dedicated Codex inbox's clean worktree remains at `fc1e202`, older than the
merged bridge revision. Before gameplay delegation, explicitly select/synchronize
the intended QA revision while the inbox is idle and then load its current rules.
No account, server, tutorial state, crop resources, or active controller was
established. The earlier Mac observation defects remain historical findings;
they were not revalidated against a loaded Windows game.

See [readiness evidence](evidence/game-readiness.json). Gameplay readiness is
**BLOCKED**, not a game test failure.

## Repository and next steps

PR #2 was merged by `dunadain` at `2026-09-16T11:33:58Z`, producing `e35cd54`.
The agent performed no merge. Fetching confirmed that its tree matches the
previous deployed bridge commit. This inspection continues on
`codex/farmqa-verification-followup`, based on the fetched `main`.

1. Before game control, establish Linear Stop cancellation and exclusive
   controller ownership. Neither is implemented by this inspection.
2. For the first supervised game run, establish a connected Editor or identified
   TestHooks device, intended QA revision, designated test environment/account,
   actual loaded build/session identity, and trustworthy state observations.
3. Then run the existing bounded one-plot scenario, preserve its trace, and repeat
   only after the first journey has a supported verdict.

The temporary HTTPS tunnel, logged-in Windows session, and running Codex app are
still required. This inspection does not establish unattended reliability.
