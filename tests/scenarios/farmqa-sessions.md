# FarmQA session routing and pinned targets

Purpose: verify separate conversations and durable routing with gameplay off.
Local fixtures do not count as live Codex/Linear verification.

1. Run `python3 -m unittest discover -s tests -p 'test_*farmqa*.py' -v`.
   Verify migration on a private ledger copy preserves existing event states
   and destinations. Configure the saved QA project and opt into session routing.
2. Start fresh FarmQA agent sessions on two test issues. Ask the first to
   remember a harmless word and the second to return a different fixed phrase.
   Confirm two actual Codex task IDs, distinct from the legacy inbox. A pending
   `clientThreadId` is not an actual task ID.
3. Match both final replies to the correct session's Codex turn marker, Linear
   activity, and `sent` ledger row. Inspect the visible Linear replies.
4. After the tasks become idle, restart the receiver and send a follow-up in
   the first session. Confirm the same task answers with its remembered word;
   no duplicate task or earlier message is created/dispatched.
5. Start a harmless bounded waiting request in the first session, then send
   Linear Stop. Confirm its ordinary reply is suppressed and the actual task
   is named in the manual Stop instruction. A request to the second session
   must still complete. Click Stop in the first task; verify its matching turn
   ends `interrupted` before confirming stopped execution.
6. Pin a locally available client ref and test environment using `set-target`.
   Submit a new message. Change the session default, then submit another.
   Confirm the two jobs retain their individual snapshots across a restart.
   Do not open Unity or change game state; selected commits are unverified
   against the actual loaded build.

If task creation is uncertain, keep the durable hold and inspect existing tasks.
Do not erase the binding marker or retry creation. Failed/unknown delivery is not
a pass. Automatic Codex interruption and machine control remain outside this test.
