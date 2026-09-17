# Fresh-import attempt interrupted by Editor crash — 2026-09-17

**BLOCKED: Unity crashed during the requested project switch. The fresh import
did not start.** This is an operational failure, not a successful import test.
The user reported the crash; investigation confirmed it. Do not retry the switch
automatically or present the prepared copy as a tested build.

PR #11 was verified merged at `3256225`. A separate independent client clone was
prepared at `.local/clients/farmqa-fresh-7dbf23b` under the main FarmTestAgent
checkout, pinned to `7dbf23bef80c660ceb5d384c2e99cff029e5b79a`. Its 3,593 LFS
files and 15,884 tracked inputs were hashed; the checkout was clean and Library
was absent. The existing recovered QA copy was preserved.

Before switching, the recovered Editor was idle with Play Mode off, no running
tests, one clean scene and no prefab stage. A read-only snapshot found 169 Spine
atlas assets and 170 material/texture references, all with the intended supported
URP shader and available textures/importers. This is structural evidence only;
no fresh comparison or rendering test ran. The QA baseline suite passed 121 tests.

The agent scheduled `EditorApplication.OpenProject` to close the recovered QA
project and open the fresh copy with a separate log and Win64 target. The Editor
did not complete that transition while in the background. After the agent brought
the existing Unity window forward, window activation timed out, the old window
disappeared, and Unity processes subsequently exited. The original Editor log
contains shutdown cleanup followed by `Crash!!!`. Windows Application events
1000/1001 also record Unity crashes at approximately 14:08 local time. The exact
native failure cause is not established; do not assume the API call or window
activation alone identifies the underlying engine defect.

No fresh Editor log or Library was created. The agent paused the fresh-import
work after the user's correction and did not retry the launch/switch. Unity was
closed at the last observation. Revalidate process state before any recovery.

Both the original client and the recovered QA copy were compared with their
pre-attempt snapshots after shutdown: tracked status, dirty-file hashes and Git
index hashes were unchanged. No Play Mode, source fix, scene save, asset repair,
deployment restart or gameplay operation was performed in this attempt.

Private evidence is in the main QA checkout's `.local/fresh-import/`: preparation
and input manifests, recovered atlas snapshot, switch result, preserved crash
tail, post-shutdown snapshots and `failure-summary.json`. Raw crash diagnostics
remain private. The existing controlled-build log also retains the shutdown
record. No positive build manifest was generated for the fresh copy.

Recovery must first restore the intended Editor availability and inspect the
shutdown failure. Preserve both copies and all logs; do not delete a Library or
repeat this project-switch route to manufacture a fresh-import result.
