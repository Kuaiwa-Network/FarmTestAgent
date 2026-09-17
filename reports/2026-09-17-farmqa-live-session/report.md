# Dedicated account and live session verification — 2026-09-17

**PASS for bounded live session identity checks.** An authorized dedicated account
was provisioned on **公共测试服**, Unity logged in, the expected player/route
matched, deliberately wrong expectations mismatched, and leaving Play Mode made
the identity unavailable. One shop-startup Console error occurred; this is not a
clean gameplay run or a completed planting journey.

The user explicitly requested creating a dedicated account for tests on the
public test server. Its account name, player ID and last-verified route hash are
stored in the main QA checkout's ignored `.local/farmqa/test-accounts.json`, alias
`farmqa-windows-public`. Preserve and reuse this account; no tokens or passwords
were saved. Server-returned credentials were kept only in process memory during
provisioning. The in-game login uses the existing SDK-off test login path.

## Target and preparation

Original client `D:/AgentWorkSpace/Farm/Farm-Client`, commit
`65feb61d4b9c6a7f79cee6efefdfea88140219dc`, Unity 2022.3.62f3,
StandaloneWindows64; instance `Farm-Client@6d4c4b2750085821`. One Editor was
connected, no controller requests existed, and StartScene was clean in Edit Mode.
FarmQA PR #12 was verified merged; this report is on its follow-up branch.

The checkout had advanced while the Editor still held an older HotUpdate module.
Its PDB had eight source mismatches and named the removed `CakeRefRules.cs`.
The first script-compilation request failed with CS2001 for that removed file.
A forced asset-database refresh recognized the deletion and compilation/domain
reload completed. The loaded HotUpdate MVID became
`c21a2cb3-b894-4cbc-9dbb-6024685fc399`; all 1,297 available source documents
matched. The other three core modules also matched their disk MVIDs/PDBs and
available source documents. One generated document per module remains unavailable;
this is still not a complete build-provenance attestation. Console errors were
zero after refresh and before login. Original source/index snapshots stayed equal.
No source repair, settings restoration, project switch or Editor restart was used.

## Trace and observations

1. Read the server directory used by the client. Eight entries were reachable;
   selected the exact public-test entry by name. The operator's first provisioning
   request used the directory's base URL and got HTTP 404. After reading
   `ServerListRules.LoginEndpoint`, the helper added `/login`, matching the actual
   client. This was an operator-helper mistake, not a game defect.
2. POSTed the user-authorized new test-account name to that server's login endpoint
   with the same account-login form shape as the SDK-off client. Result was 1
   (success), with an assigned numeric user ID and route. Saved only the expected
   player ID and SHA-256 of `ws://Host:Port/` privately, discarding the token.
   The expected identity therefore came from the selected server before observing
   Unity, rather than copying the session reader output to manufacture a match.
3. Entered Play Mode and observed LoginView. SDK was disabled in the existing
   configuration; no SDK toggle was changed. Set `serverCombo` to 公共测试服 and
   `txtInput` to the dedicated account using driver setup shortcuts.
4. Injected one `GameTestDriver.Click("btnStart")` pointer gesture. Its completed
   result reported success and hit `GRoot..btnStart`. This was the only pointer
   gesture; no direct-login service fallback was needed.
5. The active view became StoryPlayView, with MainView underneath. An unobscured
   Unity screenshot showed the introductory story. No story click, skip, planting,
   purchase, reward grant or GM operation was issued.
6. The authenticated probe reported generation 2 before/after, authentication true,
   transport connected, stable session objects, and matching player and route.
   The standalone CLI confirmed `session_match: match`.
7. Ran two further CLI observations with intentionally wrong private expectations:
   player ID +1, then an all-zero route hash. Both reported `mismatch`; neither
   altered the game session. All results retained `execution_enabled: false` and
   verdict BLOCKED because this diagnostic never grants an action permit.
8. Login/startup emitted `[ShopService] QueryShop(13) failed: 2`. Source inspection
   ties the message to a nonzero query response code at ShopService.cs:67. The
   meaning/cause of code 2 for this request was not investigated; it is not proof
   of an authentication failure. Keep it as an observed startup finding, not a
   diagnosed product defect or an ignored clean-console pass.
9. Stopped Play Mode through `manage_editor`, leaving the Editor open. The reader
   returned `edit_mode`, match unknown, execution disabled. StartScene was clean,
   source/index/dirty-file snapshots still matched, and the account was preserved.

[Redacted verification](evidence/verification.json) contains checks, exact module
IDs and hashes of private run records. [Visible story screen](evidence/session-visible.png)
confirms UI entry, not full rendering correctness. Private run details are under
`.local/session-live/`; keep them out of Git. No raw game log dump was saved for
this login observation.

## Limits and next steps

This verifies one authenticated session and wrong-expectation rejection on this
build/server, plus Edit Mode rejection after Stop. It does not verify reconnect,
replacement during an actual asynchronous observation, or every URI/schema failure
branch. The standalone diagnostic is not wired into the controller/receiver and
still cannot authorize actions. Physical ownership, bounded action cancellation
and remaining build evidence need a separate increment before an autonomous
worker. The current server route must be revalidated on later logins.

The account is reserved for FarmQA and remains at the introductory-story state
last observed; next login must rediscover actual progress. Next development work:
use the now-verified session observation in the controller readiness design and
verify physical action ownership/cancellation. Investigate the shop query separately
when extending gameplay coverage. Spine defaults stay deferred per user decision.
