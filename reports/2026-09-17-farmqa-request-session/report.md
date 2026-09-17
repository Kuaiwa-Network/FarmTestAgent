# Request-bound session observation — 2026-09-17

**PASS for the bounded diagnostic.** The account/server observation is now bound
to an active controller request with immutable private expectations. A Stop during
a live matching sample invalidated the request. No action permit or worker was
enabled; the fixture adapter and production receiver are unchanged.

## Target and preparation

PR #13 was confirmed merged at `ab35f82`. Work continued from that merge on
`codex/farmqa-request-session` in the existing isolated QA worktree. The deployment
checkout and its local changes/runtime state were preserved.

Preflight discovered original client `D:/AgentWorkSpace/Farm/Farm-Client` at clean
`b8170a559909fccc21b488e47584f20e02a42104`, Unity 2022.3.62f3,
StandaloneWindows64, instance `Farm-Client@6d4c4b2750085821`. The source had advanced
through cooking changes while the Editor retained the preceding HotUpdate module.
A forced asset refresh/compilation in the existing open Editor completed with zero
Console errors. No restart, project switch, source edit or settings repair occurred.

New HotUpdate MVID: `74aa1b33-262f-4ebd-ace7-dd394e7eca20`. The four loaded core
modules match their disk DLL/PDB identities and available PDB source checksums:
1,297 HotUpdate documents, 302 MCP Editor, 19 AOT and 15 Nova. Each still has one
unavailable generated document; this is not complete build-provenance attestation.
The client source/index stayed unchanged through refresh and the live run.

## Live trace

- Reused the previously authorized dedicated account on 公共测试服. A fresh call
  to the selected directory entry's login endpoint confirmed the existing player
  ID and independently established the route expectation. Credentials stayed in
  memory; private account details/expectations remain outside Git.
- Entered Play Mode. LoginView already held the intended account/server fields;
  the helper verified them without changing them. Marked Console and sent one
  50 ms `GameTestDriver.Click("btnStart")`. It completed successfully at
  `GRoot..btnStart`. No direct-handler fallback or repeated gesture.
- The first Task-result observation snippet used an incorrect nested type name
  and failed to compile. The corrected observation read the already-completed
  Task through its Result property. This was a QA observation mistake; it did
  not replay the click or modify client code.
- Observed StoryPlayView with MainView underneath, also confirmed by the
  [visible session screenshot](evidence/session-visible.jpg). No story advance,
  crop action, purchase, reward grant or GM mutation was issued.
- The [replay harness](../../tests/probes/run_request_session.py) used a new
  private SQLite database with real controller/bridge code, synthetic signed
  events and mocked outgoing delivery. It ran these real read-only Unity cases:

| Case | Result |
|---|---|
| Correct pinned expectation | Source, Editor, session and current request match |
| Wrong player ID | Session mismatch; aggregate unknown |
| Wrong route hash | Session mismatch; aggregate unknown |
| Wrong HotUpdate MVID | Editor mismatch; aggregate unknown |
| Synthetic Stop after real session sample | Session match retained; request-current mismatch; aggregate unknown |
| Further inspection by stopped owner | Rejected before remote observation |
| Exit Play Mode, inspect new synthetic request | Edit Mode status; aggregate unknown |

All results retained `verdict: BLOCKED` and `execution_enabled: false`. No action
rows were created. Synchronous diagnostics released their synthetic reservations
after observation; the Stop case ended cancelled. This does not establish that
Stop cancelled any physical game input or interrupted a Codex turn.

The same startup error recurred: `[ShopService] QueryShop(13) failed: 2`.
It remains the unclassified shop-startup finding from the prior login, not a clean
gameplay result. Source edits were not attempted.

## Validation and final state

The 145-test merged baseline passed. Fourteen new tests exercise actual SQLite
reservations with controlled external observations, plus two replay-assertion
tests; final full suite: **161 tests passed**. Review requested clearer binding-deletion
and post-sample-expiry coverage; both are now exercised. It also found that the
replay's negative cases accepted any aggregate unknown, including an unrelated
failure. The replay now requires the intended mismatch with other checks matching;
two regressions failed before this change and passed afterward. This assertion
change followed the live run; all six saved live observations were then checked
against the stronger final assertions. The diagnostic implementation was unchanged.
The initial test failures
also exposed a test helper's incorrect DB-path attribute and unclosed secondary
connection; both were corrected before the passing run.

Unity was left open in Edit Mode on clean StartScene. Source/index snapshots match
preflight, the production queue remains empty, and the production DB has neither
new session-diagnostic table. The receiver was not restarted/upgraded. The private
account remains preserved at the observed story state.

[Redacted evidence](evidence/verification.json) contains target, modules, cases,
login result, cleanup checks and hashes of private evidence. Full local evidence
is under `.local/request-session/` in the main QA checkout. Binding rows contain
private player/route identifiers; only allowlisted observations are published.

## Limits and next step

The new [library](../../tools/README-farmqa-request-session.md) is deliberately
read-only. It does not create a persistent session lease or grant permission for
an action performed later. Reconnect, session replacement, domain reload, actual
network loss/process death, complete build provenance and unrestricted MCP/OS
callers remain outside this verification. The Stop event was injected locally
after a real probe response; live Linear Stop transport was not retested.

Next: perform account/route/session-generation validation in the same Unity
operation that admits one allowlisted action, preserving action-ID fencing and
cancellation/uncertain-delivery rules. Verify that on a counter-only panel while
authenticated before permitting an actual game control. Avoid extending this
diagnostic result into a reusable gameplay permission.
