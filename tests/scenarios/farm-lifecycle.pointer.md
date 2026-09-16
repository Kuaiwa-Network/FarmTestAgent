---
id: FARM-PTR-001
status: prepared-unverified
platforms: Unity-Editor, Android-TestHooks
driver: GameTestDriver-pointer
runner: supervised; NOT executable by current qa_run.py
---

# One plot: plant → water → mature → harvest

No successful live trace exists yet. This is a source-grounded learning/replay
specification, not a claimed executable or validated journey. Client/contract sources
and uncertainties are in `knowledge/gameplay/planting.md`.

## Required run parameters and gates

Record actual target/build, test environment identity, account alias, player/zone,
controller ownership, and console mark. Select a crop that is unlocked (level ≥1)
and configured for one harvest; confirm one unlocked empty plot and at least one
water. Record actual crop ID/config and plot ID in the run, not here as permanent data.
Verify own-farm context; capture tutorial and overlay state. Check `btnPlantAll` is
off before choosing a crop; if it cannot be observed reliably, stop before planting.

Observation gate: a populated typed slot must include slot/crop IDs, Watered,
HarvestTime, HarvestCount, Mutant and (when available) GrowthVersion. Inventory and
water must have valid typed counts; a missing field is not zero. On current build,
generic DumpModel fails this gate. Use an explicit, logged, read-only typed projection
or a client-fixed snapshot; never infer server acceptance from optimistic values.
Require a passive operation ack/push observation or another independently verified
server-backed signal for the pointer-triggered action. A second direct gameplay
request is not an observation.

Budgets: 20 gestures / 15 minutes, UI outcome 5s, server outcome 10s, maturity 120s;
one reasoned recovery per blocked step. Timeouts are QA limits, not product SLAs.

## Steps and assertions

| Step | Starting state and target | Command template (fill from fresh observation) | Required result |
|---|---|---|---|
| 0 | Identified test login; current login or preceding screen | If login setup is needed, record Input/SelectCombo as setup; Click current start/enter control. If already logged in, verify actual identity, never trust MainView alone. | Own farm/MainView visible; identity matches; record whether entry interaction was exercised or pre-established. |
| 1 | Own farm, unlocked empty slot, unobstructed current plot hit point | Editor `await GameTestDriver.ClickAt(x,y,50)`; Android `click_at(x=x,y=y,hold_ms=50,device=label)` | Injection completes; PlantPopup appears within UI bound; selected slot known; capture screenshot/tree. |
| 2 | PlantPopup, single-plot toggle off, selected crop cell resolved by current title/ID/level | `await GameTestDriver.Click(path,50)` or ClickAt current cell center if names are ambiguous; device `click`/`click_at` equivalent | Popup closes; only chosen plot receives selected crop; sprout/water cue visible; no unexpected other-slot/resource changes; authoritative planting evidence recorded. |
| 3 | Confirmed planted sprout, animations settled | ClickAt newly resolved plot hit point | WaterPanel visible; btnWater reachable. |
| 4 | WaterPanel; same planted slot and ≥1 water | `await GameTestDriver.Click("btnWater",50)`; device `click(path="btnWater",hold_ms=50,device=label)` | Same nonzero crop remains, Watered=true on authoritative state; water charge consistent with contract (1, accounting for separately observed regeneration); animation/result visible; empty slot can never satisfy this assertion. |
| 5 | Watered crop | Observe only; poll typed state and visible plot mode to deadline | CropId remains selected, Watered=true, and HarvestTime=0 or trusted game/server time ≥ HarvestTime; mature visual and reachable harvest panel agree. Do not require a countdown if immediately mature. |
| 6 | Mature plot | ClickAt freshly resolved plot point | HarvestPanel visible; no overlay blocks btnHarvest. |
| 7 | HarvestPanel for same crop/slot | `await GameTestDriver.Click("btnHarvest",50)`; matching device command | Authoritative harvest success; configured final harvest clears slot; correct normal OR mutant reward counter increases with matched reward evidence; visible harvest feedback; no new relevant console error. |
| 8 | Completed one-plot journey | Read-only final snapshot and screenshots | No other plots were changed unexpectedly; state persists in a subsequent authoritative observation. Record cleanup or leave resulting state explicitly. |

Currency/seed consumption is not asserted from old scenario text. Use the actual
approved contract/config for the selected crop. Unexpected multi-harvest or mutant
state is not silently rewritten into a pass; evaluate the explicit branch or mark
the scenario prerequisite unsupported, retain evidence and refine with authoritative guidance.

## Replay and Android

After a successful learning pass, preserve the exact awaited calls and condition
results, turn resolution hints into verified selectors with current geometry lookup,
and run again on equivalent test data. Only then label the journey replay-validated.
Android repeats intended steps/assertions with fresh device/build/geometry and state.
It does not reuse Editor coordinates or imply OS touch/keyboard/system Back coverage.

At every gesture record injection `success/reason/hitTarget` AND outcome evidence.
Fail an established violated assertion; BLOCKED for missing prerequisites;
INCONCLUSIVE for untrustworthy/missing observations. Never replace failed input with
Tap, direct service calls, PlantCrop/Water/Harvest, GM clock changes or purchases.
