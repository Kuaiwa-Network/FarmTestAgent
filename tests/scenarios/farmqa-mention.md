# FarmQA mention connection test

Status: PASS on 2026-09-16, Windows deployment, FARM-1188: real user mention and
follow-up produced the exact visible replies and matched confirmed delivery
records. See [live evidence](../../reports/2026-09-16-farmqa-windows/evidence/live-delivery.json).
Duplicate/restart checks remain synthetic; this establishes no gameplay coverage.

Prerequisites: private FarmQA app activated in the intended workspace and Farm
team, receiver authenticated as FarmQA, signed webhook route publicly reachable,
operator's selected test issue. No game runtime or account needed.

1. Select FarmQA from the comment editor's `@` menu and send `@FarmQA hello`.
   Expect one agent session and the exact fixed reply documented in
   `tools/README-farmqa.md`. Record issue URL, session/activity ID, elapsed time,
   visible reply and local `sent` status. A 10-second observation budget follows
   Linear's first-activity guidance, not a Farm gameplay SLA.
2. Reply `hello again` in that session. Expect one new fixed response. Record the
   incoming prompt activity ID and outgoing activity ID.
3. Automated negative case: run `test_bad_signatures_stale_and_wrong_identity_never_send`
   and the HTTP rejection test. Expect HTTP 401/403 and zero outgoing mutations
   for invalid events. Label these synthetic evidence, not Linear delivery.
4. Automated duplicate/restart case: replay the unit-test signed event twice,
   restart and replay it again. Expect one outgoing fake API call. Do not forge
   production events or mark the live duplicate behavior verified from this test.

PASS for the live connection requires the visible Linear reply and confirmed
matching outgoing mutation. Accepted webhook alone is INCONCLUSIVE. API failure
is FAIL for integration delivery; absent credentials/network is BLOCKED. No
gameplay coverage is established by any result in this scenario.
