# Suggested client and driver improvements

These are development recommendations, not modifications. Evidence and reproduction
links are in `report.md` and `knowledge/issues.md`. Paths below are relative to the
actual client `/Users/elendil/WorkSpaces/Farm/Farm-Client`, revision 688da4652.

## First: make observations trustworthy

1. **P1 — Add a typed, versioned QA snapshot.** `Core/TestDriver/GameTestDriver.cs`
   delegates to `Packages/com.kuaiwa.nova/Runtime/Utils/DumpUtil.cs:107`, which enumerates
   fields. Prefer explicit DTOs for slots, crops, currencies, water, tutorial state and
   server time, serialized with required defaults. Include schema version and explicit
   unavailable/error markers. Avoid a broad change to every debug dump. Acceptance:
   current protobuf objects round-trip nonzero AND zero/false values; a populated
   model never becomes `{}`; all returned payloads parse as JSON.
2. **P1 — Expose a safe session identity.** Add `GetSessionIdentity` with account alias,
   player ID, zone, actual connected environment/server ID and connection state. Current
   PlayerModel has account/player/zone fields but also Token, so dumping everything is
   unsuitable evidence. Preserve identity across reconnect with an explicit generation;
   reject testing on unknown or mismatched identity. Acceptance: runner rejects an
   existing MainView session for another account/server, including when its requested
   login is never attempted. Never include auth tokens in QA snapshots.
3. **P1 — Expose passive operation completion/provenance.** PlantService makes optimistic
   changes before network success (`PlantService.cs:63,95,230`). Provide a read-only
   bounded ring of request ID, action/slot, ack code, notification sequence and resulting
   state revision; mark optimistic versus server-applied snapshots. It must observe
   the request caused by the pointer action without issuing another request. Acceptance:
   rejected and delayed actions cannot pass from optimistic state; harvest assertions
   correlate slot transition and normal/mutant reward to the same operation.

## Then: bind replay to the correct target

4. **P1 — Put build and capability identity in DeviceAgent hello and Editor snapshot.**
   Include immutable build ID, Git revision/dirty manifest, platform, Unity version,
   driver schema/capabilities, hot-update DLL and config hashes. HybridCLR makes APK
   identity alone insufficient. Do not use a random device label or app version 1.0
   as build identity. Acceptance: Editor and installed Android build can be distinguished
   and the report names the exact loaded gameplay/driver content.
5. **P1 — Select C# references by target/build, not directory preference.**
   `tools/device-mcp/compile_cs.py:29,57` prefers StandaloneOSX; `server.py:281` does
   not pass a device build reference set. Require an explicit matching reference
   manifest; reject an unknown/mismatched build before compiling/injecting. Acceptance:
   with macOS and Android artifacts present, an Android request uses only its matching
   set, and stale/missing references fail clearly. Keep fixed observation tools usable
   without arbitrary injected assemblies.
6. **P2 — Give UI and scene observations stable semantic targets.** Extend current UI
   tree with crop ID/data binding, toggle selected state, clipping/effective visibility
   and active modal information. Add read-only scene targets (plot ID/mode, active
   collider hit point, current camera, screen bounds and safe area). Existing GuideAnchor
   and PlotController can supply identifiers; do not add privileged action methods.
   Acceptance: resolve the selected crop/plot after scrolling, zooming or rotation
   without hard-coded coordinates or ambiguous recycled cell names.

## Keep the first replay small

7. **P1 runner correctness / P2 pointer replay — improve the existing runner after learning.**
   Require the same nonempty crop before/after water; reject missing schemas instead
   of returning inventory 0; mark console before login/setup; preserve warnings separately;
   require authoritative harvest/reward evidence. Add only the needed awaited pointer
   operations, bounded conditions, explicit target and action records for FARM-PTR-001.
   Reject unsupported scenario documents before any state-changing step. Stop on failure,
   save screenshot/tree/console/typed state together, and do not retry non-idempotent
   requests automatically. Acceptance: QA-002/003/004 fail safely, blocked-input negative
   control is detected, and one successful learned journey replays twice.

The infrastructure tests in this report are not evidence of Android OS touch, native
keyboard, pinch, system Back, server correctness, or farm playability. Those need
separate, explicitly identified coverage after the basic journey.
