# FarmQA manual Stop verification — 2026-09-16

Outcome: **PASS for manual interruption and post-Stop recovery.** Linear Stop
alone still does not interrupt active Codex work. This was a harmless waiting
request on [FARM-961](https://linear.app/kuaiwagames/issue/FARM-961/版署版本-成就与名字),
not a gameplay test.

The FarmQA receiver, tunnel, and Codex inbox were healthy and idle before the
test. On the existing FarmQA session, the user asked the agent to wait 90 seconds
without changes or game tools, then reply `STOP TEST COMPLETE`. The bridge
acknowledged the new event and dispatched it into **FarmQA Linear inbox**. The
exact Codex turn `01a0aa68-e62a-7f11-986e-009a0f4566ac` entered `inProgress`.

While that turn was running, the user sent **Send stop request** in Linear. The
authenticated signal was recorded at 21:30:45.524 Asia/Shanghai; FarmQA's
explicit limitation error was confirmed in Linear 1.903 seconds later. The user
then reported clicking **Stop** on the Codex task. The matching turn ended with
the actual status `interrupted` after 80.194 seconds total, before the requested
90-second wait completed. This status was read from the Codex task and matched
the bridge's event marker and durable `turn_id`.

The affected event ended `cancelled` with `stop_outcome=interrupted`; its temporary
prompt and reply fields were cleared. The reserved ordinary response activity
was absent from Linear. The stop signal, FarmQA's error activity, and the missing
ordinary response were checked against Linear's API; the error was also visible
in the FARM-961 agent chat.

The user sent a newer follow-up in the same session: `After manual Stop, reply
READY.` It had an authored timestamp after the stop cutoff, dispatched to a new
Codex turn `01a0aa6a-a840-7122-b083-b8cb2b83843d`, and finished `completed`.
The exact final text `READY` appeared as a FarmQA-authored Linear activity and
was visible in the agent chat. Its event ended `sent` in 12.914 seconds with
temporary content cleared. No game or client state was touched.

[Allowlisted evidence](evidence/live-manual-stop.json) contains activity and turn
IDs, timings, hashes, terminal states, and explicit API/UI verification results.
It contains no credentials, user message bodies, or private bridge configuration.
The previous [Stop report](../2026-09-16-farmqa-stop/report.md) remains the record
of the earlier two turns that completed normally after Linear Stop; this later
test establishes the separate manual fallback.

Remaining gate: the installed Codex desktop connector still exposes no supported
active-turn interrupt operation to the bridge. A user click achieved this
interruption; FarmQA did not issue an automatic interrupt. Also establish an
exclusive game controller and an identified test account/environment before
enabling gameplay. The temporary tunnel and logged-in desktop remain prototype
hosting requirements.
