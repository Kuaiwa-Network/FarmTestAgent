# FarmQA Stop handling

Scope: bridge control only. No game execution, filesystem changes by the inbox,
or game/client/server mutations. The current desktop connector cannot interrupt
an active turn. Never call this scenario a full automatic cancellation pass.

## Local regression coverage

Run `python3 -m unittest discover -s tests -p 'test_*farmqa*.py' -v`.
Cover authenticated stop parsing (including no body), invalid signature/session,
queued cancellation, duplicate/restart handling, delayed pre-stop messages, newer
messages, missing authored time, session isolation, stop during idle check,
dispatch, result reads and final send, ambiguous dispatch, uncertain final
delivery, and acknowledgement failure across restart. Assert no unwanted dispatch
or ordinary reply, not just an HTTP response.

## Live supervised check

1. On an existing authorized Farm test issue, ask FarmQA to wait for 60 seconds
   without changing files or game state, then reply `STOP TEST COMPLETE`.
2. While its exact Codex turn is running, use **Send stop request** in Linear's
   agent chat menu. Confirm a real authenticated Stop control record arrives.
3. Expect an explicit limitation error if execution is still active. Verify the
   job is `stop_pending`; do not count this error as proof of interruption.
4. Manually click **Stop** in the dedicated Codex inbox. Check the exact turn's
   actual status. If it finishes before interruption, record `completed`, not
   `interrupted`; the late ordinary reply must still be suppressed.
5. Match the visible Linear stop reply to `stop_requests.activity_id`, the job's
   `event_key` / `turn_id`, and `stop_outcome`. No final `STOP TEST COMPLETE`
   should be sent after the accepted stop unless its write was already in flight.
6. Send a fresh short follow-up after terminal confirmation to verify that a
   newer authored event can resume. Never force a replay of an ambiguous write.

Current local result: 46 tests PASS. Live Stop and post-stop resume are pending.
Automatic interruption remains BLOCKED by the installed connector's capabilities.
