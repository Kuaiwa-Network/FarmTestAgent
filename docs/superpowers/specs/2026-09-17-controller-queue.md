# FarmQA controller reservation queue

Implements the scheduling part of the user's approved single-controller design
in CLAUDE.md. Gameplay and direct Unity/computer actions remain disabled.

One local SQLite ledger represents one shared controller. An operator explicitly
queues an existing authenticated bridge event with a pinned target. Enqueue
copies that event's target, session, organization and source timestamp; it never
uses the current session default. Repeated enqueue of the same event is idempotent.
Unspecified/malformed targets and stopped events are rejected.

The oldest queued request can be reserved by one worker. BEGIN IMMEDIATE and a
unique active-slot index serialize independent processes. Each reservation gets
an unpredictable token, retained only in private state and the worker's memory.
There is no expiry or automatic takeover: after a crash, the active reservation
continues blocking acquisition until the original owner explicitly releases it.
This is a scheduling reservation, not a physical lock over arbitrary Unity tools.

Authenticated Linear Stop applies its existing source-time cutoff to requests
in that organization and session. Queued requests become cancelled; an active
request becomes cancel_requested and retains the slot. Newer requests and other
sessions are unaffected. Duplicate Stop cannot cancel later work. Enqueue checks
the saved Stop history, preventing delayed promotion of an old event. Release
after Stop records cancelled, never completed. A wrong token cannot release or
inspect an owner's reservation. Release is idempotent for the same owner.

The public CLI exposes only enqueue and redacted status. Worker acquire/release
are local library interfaces for the later controller runner; no live worker or
force-unlock CLI is introduced. Status does not disclose tokens or message text.
No target observation is invented, no branch is checked out, and no tests run in
Unity. Loaded-build verification and bounded action cancellation remain required
before a game-action adapter is enabled.
