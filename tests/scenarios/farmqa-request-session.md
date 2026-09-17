# FarmQA request/session observation

Scope: supervised read-only diagnostic, Windows Editor. No gameplay permit.

1. Verify one exact Editor/project/source/build/module target and no other controller
   owner or running pointer/test. Preserve client files and existing account progress.
2. Revalidate the dedicated `farmqa-windows-public` account and 公共测试服 route
   independently through the selected server directory/login response. Save only
   the expected allowlisted fields privately; discard credentials.
3. Enter Play Mode, observe LoginView and the account/server fields. Use setup
   shortcuts only if those fields need setting, and record that coverage gap.
   Mark Console and issue one `GameTestDriver.Click("btnStart", 50)` via MCP.
   Retain its Task; observe completion before reading Result. Never repeat an
   uncertain login click or fall back to a direct handler.
4. Within the ten-second server-result observation budget, verify authenticated
   session identity. Capture active views and visible UI; do not advance the story.
   Record startup errors separately from identity assertions.
5. Run `tests/probes/run_request_session.py` in authenticated mode with the current
   full client SHA and private expectation file, writing a new ignored directory.
6. Expect all four checks to match only for the correct case. Wrong player/route
   must report session mismatch; wrong module must report Editor mismatch. A
   synthetic Stop delivered after the real session probe must retain the session
   match but invalidate the request. A later inspection by that stopped owner is
   rejected before remote reads. Every result keeps execution disabled.
7. Exit Play Mode and repeat the harness in edit-mode with a second new directory.
   Expect `observation_status: edit_mode` and no request/session match.
8. Verify clean Edit Mode, unchanged source/index, unchanged production queue/schema,
   and no dispatched controller actions. Save redacted traces and the report here.

Python regressions additionally cover ownership/target/binding changes during
reads, immutable bindings after inspector reconstruction, late expiry, malformed
observations, busy/changed targets, error redaction and transaction misuse. These
controlled samples do not claim a real reconnect or transport interruption.
