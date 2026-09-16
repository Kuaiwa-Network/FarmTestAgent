# FarmQA follow-up verification and Windows readiness

Date: 2026-09-16. Scope: recheck the deployed bridge, prepare a genuinely new
Linear session test, and inspect gameplay prerequisites. No gameplay ran.

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
**New `created` session and follow-up verification remain pending.** Match both
visible replies to actual Linear activities, completed Codex turns, and the ledger
before changing this verdict. A repeated mention on FARM-1188 previously reused
its existing session and is insufficient evidence for the `created` path.

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

1. Finish the real new-session and follow-up test when the user provides the
   mention/issue; inspect failures before changing bridge code.
2. Before game control, establish Linear Stop cancellation and exclusive
   controller ownership. Neither is implemented by this inspection.
3. For the first supervised game run, establish a connected Editor or identified
   TestHooks device, intended QA revision, designated test environment/account,
   actual loaded build/session identity, and trustworthy state observations.
4. Then run the existing bounded one-plot scenario, preserve its trace, and repeat
   only after the first journey has a supported verdict.

The temporary HTTPS tunnel, logged-in Windows session, and running Codex app are
still required. This inspection does not establish unattended reliability.
