# First gameplay guide: planting

No gameplay observation yet. Last source review: 2026-09-16. Status of all G entries
below: **inferred** (applicability to a running server/build unverified).
Client source: `688da4652c9c2c3b5702c8e99d81e1480df419f7`, Editor/Android intended.
Contract source: `Farm-Contract` revision `1543bb2581a4e82874ede830bb37bbe1658f15a0`,
`proto/plant.proto`. Its declarations are normative evidence, not runtime observations.

## Goals and intended rules

| ID | Claim / prerequisites | Authority or hypothesis source |
|---|---|---|
| G01 | Plant an unlocked crop on an unlocked empty plot. Missing slots are locked; `crop_id=0` means empty. Crop level must be at least 1. | Intended: contract `proto/plant.proto:7,22,127` |
| G02 | Watering costs one water-energy point. An empty plot or unwatered harvest is invalid. | Intended: contract Water/Harvest request and ack comments |
| G03 | A planted, watered slot with `harvest_time=0` is immediately harvestable. A zero timestamp alone does not establish maturity. | Intended: contract LandSlot; source model-state helper agrees |
| G04 | Multi-harvest crops can remain planted after a harvest; only the final harvest should empty the slot. | Contract `harvest_count`, client state; verify exact selected crop configuration |
| G05 | A mutant harvest grants one mutant crop instead of a normal crop; inventory assertions must use the actual reward type. | Intended: contract LandSlot.Mutant / RewardEntry |
| G06 | Successful operations push PlantData before their ack. Batch operations can partially succeed. | Intended: contract request/response section; first journey uses one plot |

Do not inherit the old scenario's universal “seed cost reduces currency”, one-hour
time skip, “watering always starts a countdown”, or “every harvest clears the plot”
as accepted requirements. They are unverified or conditional. Choose a single-harvest
crop and a verified reward oracle for a small first journey. No chosen crop ID yet.

## Recognizing and operating the screens

| ID / state | Recognition and route | Expected visible effect / caveats | Source |
|---|---|---|---|
| G07 Login | LoginView; old driver paths `serverCombo`, `txtInput`, `btnStart` are hints to resolve live | MainView after valid test login; gate routing/loading can intervene. No current session identified. | LoginView/LoginService; old scenario only for path hints |
| G08 Own farm | MainView plus own-farm scene context and visible Plot objects | Pick an existing slot and current Plot.Mode Empty, not just a bare patch of ground. Visit-mode plots have different behavior. | Plot.cs `OnTap`, PlotController |
| G09 Empty plot → picker | ClickAt a current plot hit point | PlantPopup shows `flowerList`, `btnPrev`, `btnNext`, crop title/count/level; main HUD may hide. | Plot.cs:211; PlantPopup.OnBind/RenderItem |
| G10 Choose/plant | Press/release current crop cell; single-plot mode | Popup closes; sprout and watering cue expected. `btnPlantAll` is a persisted per-account preference; selected state can plant all empty plots. Check it first. Drag >10px starts a planting gesture. | PlantPopup.TrackPress, RenderItem, RefreshOneKey |
| G11 Sprout → watering | ClickAt plot again, observe WaterPanel; Click `btnWater` | Water animation; plot may temporarily reject interaction during animation. Single watering uses touch-begin/release, so Tap does not cover it. | Plot.cs:216; WaterPanel.TrackPress |
| G12 Mature → harvest | When trustworthy state says planted + watered + mature, click plot; HarvestPanel then Click `btnHarvest` | Harvest effects and authoritative reward change; final-harvest slot clears. A short wait for effects is distinct from state confirmation. | Plot.cs:221; HarvestPanel.TrackPress; PlantService.Harvest |
| G13 Growing | Click shows AcceleratePanel | Do not spend acceleration items to hide maturity uncertainty. Wait within scenario budget, otherwise stop with evidence. | Plot.cs:225; contract Accelerate |

## Obstacles and recovery

- **Tutorials/overlays:** GuideTapFilter, guide camera locks and popup hit targets may
  block input intentionally. Capture screenshot/tree/controller pages and guide state;
  do not bypass the guide. A bounded learning step may follow a clearly identified
  tutorial instruction; otherwise mark knowledge gap.
- **Locked plots/crops:** confirm slot presence, plot mode and crop level before
  choosing. A locked-plot toast is not necessarily a defect.
- **Insufficient water:** verify energy before the journey. Source provides a water
  shortage toast/item route for batch/drag paths; do not assume the single-button
  feedback is identical without observing it. No purchases for this scenario.
- **Loading/closing animation:** await bounded view changes; re-dump when done.
  Do not infer failure from a sub-second observation or raw text template.
- **Wrong popup/scene:** use current tree to find an actual close/back button and click
  it; re-observe. Do not use Back as proof that player navigation works.
- **Unknown or malformed state:** stop judging that assertion; this is a driver or
  observation issue, not empty inventory. Never send a direct action to “verify” the
  pointer action, because that changes the state being tested.

## Questions retained for later learning

Which current test environment/account is designated, which crop is suitable and
single-harvest, what are the actual tutorial prerequisites, and what read-only signal
proves each pointer-triggered server acceptance? What feedback should single watering
show with no water? These are recorded gaps, not assumptions or questions to re-ask
before the infrastructure findings are reviewed.
