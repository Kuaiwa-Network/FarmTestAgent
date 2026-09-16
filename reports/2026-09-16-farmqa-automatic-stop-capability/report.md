# FarmQA automatic Stop capability check — 2026-09-16

Outcome: **BLOCKED for the existing Codex desktop inbox.** No automatic Stop
was deployed or claimed. The verified manual Stop fallback remains in place;
gameplay remains disabled.

The target was the existing **FarmQA Linear inbox** desktop task. The bridge's
configured task ID matched the task returned by the Codex app, and the bridge
already correlates each Linear event to its exact Codex turn. No FarmQA job or
Stop record was active during this inspection. The repository was at merged
`main` commit `df2b48d` before this documentation branch; 46 FarmQA local tests
passed. No live Linear Stop was sent, service was restarted, or game state was
changed for this capability check.

The [official Codex App Server protocol](https://learn.chatgpt.com/docs/app-server)
defines `turn/interrupt` with `threadId` and `turnId`; success is followed by
`turn/completed` with status `interrupted`. This requires a connection to the
App Server that owns the running turn. Its default transport is stdio. The
desktop-owned App Server on this machine used that default, had no attachable
listener, and exposed no reachable documented control socket. A separate
Codex process owned by another integration was not the desktop backend.

The installed Codex app-tools connector can read the target task and send it
messages, but its available tool catalog has no Stop, interrupt, or cancel-turn
operation. The app's handoff operation interrupts while moving a task and its
git state; it is not an appropriate Stop API. Starting a new CLI App Server
would create a different runtime and would not give FarmQA control over the
existing desktop turn. It also would not establish that the user-visible task
retains desktop computer-use capability.

Therefore the bridge must continue to cancel queued jobs, suppress the ordinary
Linear reply after Stop, hold new dispatch until the exact turn ends, and tell
the operator to click **Stop** in the Codex task if a turn may be running. The
[manual Stop run](../2026-09-16-farmqa-manual-stop/report.md) verified an actual
`interrupted` status and later recovery; it did not verify automatic Stop.

Next step: obtain a supported interrupt operation for the same desktop task
from the Codex app connector, or design and separately validate a bridge-owned
App Server runtime, including its computer-use access and task visibility.
Only then wire the exact turn ID into `turn/interrupt` and repeat the supervised
Linear Stop test. Keep the current fail-closed behavior until that live test
shows `interrupted` without a manual click.
