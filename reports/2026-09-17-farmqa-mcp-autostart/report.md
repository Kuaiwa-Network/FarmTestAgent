# MCP automatic startup verification — 2026-09-17

**PASS for one direct Editor launch.** The user enabled MCP for Unity's
Advanced → Auto-Start Server on Editor Load, then requested verification.
The saved `MCPForUnity.AutoStartOnLoad` preference was enabled. No Editor or
listener on port 9090 was running before this test, so no active Editor was closed.

Launched Unity 2022.3.62f3 visibly and directly into the recovered QA copy
`.local/clients/farmqa-7dbf23b`, pinned to client `7dbf23b`, with Win64 target
and a separate private log. The installed plugin started the local HTTP server,
reported it ready at `http://127.0.0.1:9090`, and connected the Editor session.
No manual Start Server click or project-switch API was used.

Fresh MCP discovery, selection and read-only probes verified:

- Exactly one connected Editor: `farmqa-7dbf23b@66bddd43c432dae8`.
- Correct recovered project, Unity version and StandaloneWindows64 target.
- Idle Editor, no running tests, Play Mode off and clean scene state.
- Pinned Spine shader/preset values loaded, with matching cached-asset reference.
- Zero Console errors and four core module IDs matching the controlled-build record.
- Original/recovered snapshots unchanged between this test's first and final reads.

The original checkout had advanced to `a6dce07592d32b9760d60321118abd496c5bb291`
since the earlier investigation; its existing four dirty-file records remain.
This test did not change that checkout. The QA copy remains pinned at `7dbf23b`.
The old original-checkout snapshot is therefore no longer a current baseline.

[Redacted evidence](evidence/verification.json). Full launch log and live payload
remain private under the main QA checkout's `.local/mcp-autostart/`.

This completes the pending MCP portion of Editor recovery. It does not prove
recovery from every server failure, fix the shutdown crash, complete the
fresh-import regression, or enable gameplay. Fresh-import work stays paused.

Correction to earlier advice: the installed plugin already implements automatic
HTTP startup. `Editor/Services/HttpAutoStartHandler.cs` reads the preference with
default false, waits for Editor readiness, starts the local server and connects
the bridge. The Advanced toggle writes that preference. It had been unset on
this Windows machine. No new startup implementation was needed. The Mac's
configuration was not inspected, so its exact reason for automatic connection
remains unknown.
