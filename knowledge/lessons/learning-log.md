# Learning log

## Verified lessons

L01 — **user-confirmed**, 2026-09-16; prerequisites: beginning this testing assignment;
platform/build: all. Claim: inspect available infrastructure before requesting account
or gameplay details. Evidence: user correction, “let's first inspect the infrastructures,
before asking me questions”. Mistake: account/exclusive-control question was sent before
completing discovery. Correction: complete discovery independently; retain remaining gaps
in report. Follow-up validation: infrastructure inspection completed with no more gameplay
questions; future-session behavior still needs validation.

L02 — **observed**, 2026-09-16; prerequisites: current protobuf properties through
DumpUtil; platform/build: loaded Editor assembly/client 688da4652. Claim: `{}` is lost
observation, not empty farm state. Evidence: synthetic serializer probe + two offline
runner reproductions. Adopted procedure: required-field gate before any state assertion.
Validation limit: applied in inspection; not yet replayed in a gameplay journey.

L03 — **observed**, 2026-09-16; prerequisites: Linear AgentSessionEvent fixtures;
platform/build: FarmQA v0 / published Linear SDK schema read this date. Claim:
follow-up type is `agentActivity.content.type`; a fixture with top-level `type`
can falsely validate an incompatible handler. Evidence: corrected fixture failed
with `ignored` instead of `accepted`; handler fix and full 12-test replay passed.
Procedure: compare integration fixtures with authoritative schema before judging
mocked tests. Live Linear routing remains unverified. (Infrastructure lesson only.)

L04 — **observed**, 2026-09-17; prerequisite: Spine preferences during Editor
import; platform/build: Unity 2022.3.62f3, client `7dbf23b`, Spine package
`eb588ecd57`. The `Preferences` getter can create a settings asset; it is not a
read-only inspection API. The first-import stack and changed input hashes confirm
this write path. Procedure: inspect an already-loaded asset's serialized fields
and cached-reference identity without calling `GetOrCreateSettings`. The new
probe was executed before/after recovery; two warm reimports retained restored
settings. This does not verify fresh-import prevention or gameplay. Evidence:
[import drift report](../../reports/2026-09-17-farmqa-import-drift/report.md).

L05 — **observed**, 2026-09-17; prerequisite: switching the running Windows QA
Editor; platform/build: Unity 2022.3.62f3, client `7dbf23b`. A scheduled
OpenProject transition followed by foreground activation crashed during shutdown;
the stack reaches a missing scripting manager through a focus-change callback.
The exact causal defect remains unresolved. Do not automatically repeat that
transition or activate a shutting-down Editor. The subsequent direct recovery
also exposed an operator mistake: hidden launch is inappropriate when the user
requests a visible interactive Editor. Use a normal visible launch for that
request and verify the returned window. Background helper defaults remain hidden.
Evidence: [crash and recovery report](../../reports/2026-09-17-farmqa-editor-recovery/report.md).

## Candidate lessons (not verified gameplay knowledge)

C01 — **inferred**, reviewed 2026-09-16; prerequisite: designated single-plot crop;
platform/build: source 688da4652 + contract 1543bb258. Hypothesis: first watering can
make the first harvest immediately available, so adding acceleration may be unnecessary.
Evidence: contract and PlantStateHelper. Promote only after authoritative live state.

C02 — **inferred**, reviewed 2026-09-16; prerequisite: first planting pass;
platform/build: same source. Hypothesis: persisted `btnPlantAll` selection is a major
source of unintended multi-plot changes. Evidence: PlantPopup.TrackPress/RefreshOneKey.
Validate live selected-state observation before interacting; do not store preference as fact.

C03 — **inferred**, reviewed 2026-09-16; prerequisite: future cross-platform injected
observation; build: local artifact inventory. Hypothesis: explicit target/build reference
selection is required before using run_csharp safely across platforms. The selection
problem is observed; its effect on a real Android probe remains untested.
