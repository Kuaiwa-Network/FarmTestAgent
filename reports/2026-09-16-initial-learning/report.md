# Infrastructure inspection — 2026-09-16

**Outcome: infrastructure inspected; gameplay journey BLOCKED / deferred.**
User steered this session to inspect infrastructure before asking questions. No
test-account login, farm action, purchase, server configuration change, or Android
gameplay occurred. No product defect is claimed.

## Target and build

| Item | Observed identity |
|---|---|
| QA workspace | `/Users/elendil/WorkSpaces/Farm/FarmTestAgent`, initially empty Git repository |
| Unity instance | `Farm-Client@edc12837aaf5486f` |
| Actual Editor project | `/Users/elendil/WorkSpaces/Farm/Farm-Client` |
| Reference worktree | `/Users/elendil/.codex/worktrees/9ab9/Farm-Client` |
| Source HEAD, both checkouts | `688da4652c9c2c3b5702c8e99d81e1480df419f7` |
| Compared source scope | 21 requested guidance/driver/scenario files have identical SHA-256; scoped tracked diff empty |
| Unity/runtime/selected build platform | Unity 2022.3.62f3 / OSXEditor / Android build target (not Android runtime) |
| Loaded driver | HotUpdate 0.0.0.0; module MVID `8e0f3b3d-e2b9-4030-93c8-aa4173206538` |
| Application version/build GUID | `1.0` / all zeros in Editor; insufficient to identify a player build |
| Editor state | Initially stopped at `Assets/StartScene.unity`; stopped there again after fixture tests |
| Android | ADB enumeration empty; no installed/running build identified |
| Local artifacts | APK and player DLL hashes inventoried; no claim they match current Editor or any device |
| Contract reference | `1543bb2581a4e82874ede830bb37bbe1658f15a0`, read-only `proto/plant.proto` |
| Test account/server/resources | Not established; no gameplay session used |

Full working-tree cleanliness was not established: the initial general `git status`
encountered an LFS clean-filter write denied by the read-only boundary. Later targeted
text/source checks succeeded with filters disabled. No client source edits were made.

## Results and evidence

| Check | Verdict | Evidence / scope |
|---|---|---|
| Unity custom tools, project identity and readiness | PASS | `preflight0.json`, `preflight1.json`, `editor-identity.json`; driver callable |
| Protobuf serializer preserves slot/crop state | **FAIL** | `serializer-probe.json`: populated slot → `{}`, dictionary → `[{"k":7,"v":{}}]`, crop list → `[{}]` |
| Positive pointer press/release/click | PASS | Named existing PlayMode test, exact event order asserted |
| Covered target rejects click with no activation | PASS | Negative fixture checks failure, blocker hit and no events |
| Untouchable target rejects without direct fallback | PASS | Negative fixture checks failure and no events |
| Broker argument forwarding | PASS, 4/4 | `broker-pointer-tests.txt`; mocked transport only |
| Existing broker startup and MCP handshake | PASS | `broker-preflight-retry.json`; 22 tools, including pointer verbs |
| Connected Android/build prerequisites | **BLOCKED** | ADB no devices; broker `connected=false` at the short probe instant |
| Runner identity verification | **FAIL** | `runner-audit-1.json`, `runner-audit-2.json`; claims requested account/server from MainView alone |
| Runner watering oracle | **FAIL** | Same traces; empty plot reported watered |
| Runner missing crop observation | **FAIL** | Same traces; `[{}]` interpreted as inventory 0 |
| Runner pointer capability / old scenario compatibility | **BLOCKED** for interaction replay | `click` rejected; 1/4 scenario documents parse; executable rose scenario uses direct actions |
| Injected C# target reference selection | **FAIL** for target binding | `environment.json`: StandaloneOSX chosen with Android files also present; no device execution attempted |
| Farm journey, repeat and Android parity | **BLOCKED / not attempted** | Prepared specification only; no observed gameplay trace |

Unity fixture job: `eb4d1c3d27f5488fa67aef04e2526d88`, **3 selected / 3 passed / 0
failed**, reported test execution 0.1434863s (excludes tool/setup overhead).
The job's progress metadata says `total=956` (discovery inventory); its result summary
is **3**, not a full-suite result. One fixture output warned of no audio listener in
the test scene; not reported as a product defect. Baseline console query returned
11 warnings and no errors in the returned entries; this is not a gameplay clean-console claim.

No screenshot or farm UI tree was captured because the game journey never ran.
The serializer probe uses synthetic objects, and the blocked-input checks use temporary
fixture UI. Raw pointer coordinates/results were not emitted by the existing fixture;
its per-test assertions/results are retained. These limits are explicit in the trace.

## September 16 limitations rechecked

All six remain relevant: fields-only serialization still fails current protobuf
properties; qa_run still uses direct commands; identity and watering false passes
reproduced; only one of four documents has runner syntax; pointer simulation remains
a single in-game pointer and cannot establish OS touch, pinch, native keyboard or
system Back. Previous July device milestones are historical and were not counted.

Additional observation: the compiler's preferred-directory selection can use a macOS
reference set for an intended Android script. Device hello lacks the identity needed
to verify loaded hot updates. Reported as infrastructure issues, not an observed
Android crash or gameplay failure.

## Changes made during inspection

- Created QA instructions, a small knowledge base, source-grounded gameplay guide,
  candidate/verified lessons, issues and coverage baseline in this repository.
- Added a draft pointer journey and replay instructions for existing blocked-input
  fixtures and offline runner defects. No new gameplay framework or client patch.
- Ran read-only Unity probes; ran three temporary existing PlayMode fixtures; Editor
  returned to stopped StartScene. No direct gameplay service calls.
- ADB's local daemon was started for enumeration. No install, launch, reverse mapping
  or device setting change. Existing broker launched briefly on localhost and exited.
- Default sandbox initially denied ADB/broker listener startup. Approved escalated
  retries succeeded; these were environment restrictions, not product defects or
  automatic-review rejections. Broker dependency installation was unnecessary.

## Next steps and precise prerequisites

First review [client/tooling improvements](improvements.md). Highest priority is typed
state, safe session identity, passive authoritative completion, and target/build identity.
Do not start a large replacement runner; the existing pointer driver is usable.

Before the first supervised farm journey: identify the designated test environment and
account, verify its actual session/resources, choose one unlocked single-harvest crop,
provide a trustworthy observation path for slot/water/reward plus server completion,
and establish exclusive controller ownership. The prepared scenario includes bounds
and assertions but is not labeled replayable success.

For Android: an attached/authorized device, an identified development TestHooks APK
with matching loaded hot-update/config manifest, DeviceAgent connection to the broker
and verified test session are required. Current local APKs alone do not satisfy this.

After Editor learning succeeds: save exact observed pointer calls and evidence,
validate a replay, repeat the journey, then repeat the intended journey on Android.
Add a real farm-modal negative case alongside the already verified infrastructure
negative control. See `trace.jsonl` for the exact observed inspection sequence and
`knowledge/metrics.md` for the zero-gameplay baseline.
