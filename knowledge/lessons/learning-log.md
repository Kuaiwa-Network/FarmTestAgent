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
