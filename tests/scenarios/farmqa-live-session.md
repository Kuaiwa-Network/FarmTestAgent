# Live session identity regression

Use the dedicated account alias `farmqa-windows-public` from the main QA checkout's
ignored `.local/farmqa/test-accounts.json`. The user authorized its creation on
公共测试服 for supervised tests. Do not create a new account each run, use a
historical example account, reset progress or change GM state implicitly.

1. Revalidate the exact Editor/project/build, scene state and controller ownership.
   Preserve source changes. Resolve stale compiled inputs through normal refresh;
   do not label an old module as the current source commit.
2. Select the authorized server and independently establish expected player/route
   identity from its trusted login response/configuration. Never set expectations
   from the observed sample just to make matching pass; never persist tokens.
3. Under supervised authorization, log in through the existing test login flow.
   Observe the visible result and the read-only session probe. Require stable
   authentication, connected transport and exact expected player/route match.
4. Change only the diagnostic's private expected player, then expected route, and
   require `mismatch` for each fresh observation. Do not mutate the actual session.
5. Stop the Play Mode started for this run after the requested observation, leaving
   the Editor open. Require `edit_mode`/unknown and no authenticated identity.
6. Record source preservation, Console findings, actual account state and all
   untested branches. The CLI always exits 2 for diagnostic results and never
   enables a worker; do not equate that with failed authentication.

Observed 2026-09-17: matching identity, both mismatch cases and post-Stop rejection
passed. One startup shop query returned code 2. Reconnect and autonomous action
ownership/cancellation are not covered. See
[run evidence](../../reports/2026-09-17-farmqa-live-session/report.md).
