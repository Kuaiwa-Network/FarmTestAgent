# Editor recovery after project-switch crash — 2026-09-17

The user authorized reopening the recovered QA project directly and inspecting
the crash, while keeping the fresh-import test paused. This report supersedes
the previous observation that no Editor was running. It does not establish that
the shutdown defect is fixed or authorize repeating the failed project switch.

## Crash evidence

The shutdown log reports `GetManagerFromContext: pointer to object of manager
'MonoManager' is NULL (table index 5)`, then `Crash!!!`. Its native stack includes
`DoQuitEditor`, window destruction, `ContainerWindow::OnActivateApplication`,
`EditorApplicationProxy::Internal_FocusChanged`, editor scripting class lookup,
and `GetManagerFromContext` before the error/reporting path.

Windows Application events at 14:08:19 and 14:08:25 both identify PID 25560
(`0x63d8`), the old recovered Editor, with exception codes `40000015` and
`c000041d` in KERNELBASE.dll. These are two records for that same process; they
do not prove that two separate Editors crashed.

Inference: a focus-change callback reached the scripting manager during shutdown
after the manager was unavailable. The native defect and a minimal reproduction
remain unresolved. Window activation occurred during the failed switch, but the
stack alone cannot prove that activation was the sole cause. No crash reproduction
was attempted. An official issue search found the same message in a
[different batch-build/import case](https://issuetracker.unity.com/issues/10600/batch-mode-crash-after-completing-player-build-due-to-textures);
that is not evidence of the same defect or an applicable version fix.

The raw dump remains in the existing Unity crash directory, and private analysis
and launch logs are under `.local/editor-recovery/` in the main QA checkout.

## Recovery actions and limits

Started Unity 2022.3.62f3 directly with the recovered project
`.local/clients/farmqa-7dbf23b`, Win64 target and a separate log. The first recovery
launch mistakenly used a hidden window (PID 23820). It finished initializing but
was not visible; the user confirmed no Unity window. After confirming the process
identity, sole-Editor status and unchanged tracked files, the agent terminated
that owned process and relaunched with a normal visible window (PID 16348).
The hidden launch was an operator error, not a successful interactive recovery.

The recovered QA Editor window became visible with an empty clean scene and Play
Mode off. MCP initially showed No Session; the user was asked to click Start
Server because the UI action launches a terminal command prohibited by the
computer-use instructions, and the previous direct server launch was rejected
by automatic approval review. Final MCP verification is pending below.

No project-switch API was called during recovery. Neither Library was deleted,
no fresh import was started, and no game source, package code or Editor preference
was edited. The original and recovered client tracked snapshots matched their
pre-switch snapshots after initialization. Spine settings still had pinned hash
`4d05acd845fa79d5b0c2fc1e4a0db97b70d9072797b29747af13b439e9d5af90`.

## Final verification

Pending the user's MCP server start. Do not claim live identity/settings verification
from process startup or the visible window alone.
