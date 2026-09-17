# Open issues

Reviewed 2026-09-16; source/client 688da4652. No product bug confirmed this run.

| ID | Classification / knowledge status | Finding and evidence | Resolution needed |
|---|---|---|---|
| QA-001 | Driver/observation defect; observed | Loaded serializer drops protobuf slot/crop properties. Synthetic repro `serializer-probe.json`. | Typed, versioned state snapshots; validate required fields, including default values. |
| QA-002 | Driver/observation defect; observed | Runner calls only views/mark before claiming requested account/server login. `runner-audit-{1,2}.json`. | Safe session identity read + fail closed on mismatch/unknown identity. |
| QA-003 | Driver/observation defect; observed | Empty slot `{cropId:0,watered:false,harvestTime:0}` is reported watered. Same repro. | Require same nonempty crop and authoritative watered state. |
| QA-004 | Driver/observation defect; observed | `[{}]` crop data becomes count 0, creating a false baseline. Same repro. | Reject unreadable/missing schema; distinguish absent inventory entry from malformed dump. |
| QA-005 | Driver capability gap; observed | Runner has no pointer op; only 1/4 old docs parse. | After first learning pass, extend existing runner for one recorded interaction journey and explicit assertions. |
| QA-006 | Build/observation defect; observed selection, inferred device impact | C# compiler chooses StandaloneOSX first independent of target. `environment.json` and compile_cs.py. | Bind compile references to selected device build and reject mismatch; no Android execution claimed. |
| QA-007 | Driver/observation gap; inferred | Hello exposes version/label but not exact loaded source/content identity. | Build/assembly/config manifest and capability schema. |
| ENV-001 | Environment/test-data problem; observed | No ADB devices; short-lived broker registry empty. | Attached authorized Android and matching development TestHooks build. Recheck at next session. |
| KNOW-001 | Gameplay knowledge gap; inferred | Old wheat/cost/time-skip scenarios conflict with or overgeneralize current contract semantics. | Validate selected crop, resource requirements, mutation/reward branches and live UI through learning. |

Next steps: review the infrastructure report; arrange trustworthy state/session and
build identification (client recommendations supplied); then identify a designated
test session, run the prepared journey in Editor, convert the observed trace into a
validated replay, repeat it, and run Android. Do not close blockers by weakening assertions.

## Additional finding — 2026-09-17

| ID | Classification / knowledge status | Finding and evidence | Resolution needed |
|---|---|---|---|
| ENV-002 | Import/build environment defect; observed overwrite, source-inferred initialization timing | Spine creates preferences during the first import and overwrites pinned settings with fallback values. [Report](../reports/2026-09-17-farmqa-import-drift/report.md). | Recovered QA settings remain intact; a separate fresh import reproduced the overwrite. Its 169 atlases/170 material-texture references match the recovered copy structurally; rendering and new-asset behavior remain untested. [Fresh evidence](../reports/2026-09-17-farmqa-fresh-import/report.md). Preserve source settings, validate imports and regenerate evidence before a positive identity gate. |


ENV-002 disposition, user-confirmed 2026-09-17: defer the Spine defaults fix and
leave the current copies unchanged. No impact was found in the existing-asset
structural comparison; rendering and new-import behavior are not verified. The
finding alone does not block continued readiness or existing-content testing.
Revisit on new Spine imports or observed visual differences. Separate session,
physical ownership/cancellation and build-evidence limits remain explicit.


## Session-login observation — 2026-09-17

ENV-003 / unclassified startup finding: dedicated public-test account login
succeeded, but client logged `[ShopService] QueryShop(13) failed: 2`. The source
logs this for a nonzero shop-query response; cause/expected unlock behavior was
not established. Keep separate from the session identity PASS. No shop or server
fix was attempted. [Evidence](../reports/2026-09-17-farmqa-live-session/report.md).

ENV-003 update, observed 2026-09-17: the final introductory story button reached
MainView and the first guide dialogue, while another identical shop error arrived
inside its action interval. Navigation passed; the zero-new-error assertion failed.
The root cause remains unclassified. No game/server fix or error suppression.
[Sequence evidence](../reports/2026-09-17-farmqa-story-sequence/report.md).
