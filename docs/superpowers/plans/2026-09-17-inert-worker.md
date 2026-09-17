# FarmQA inert controller worker

Approved increment: run one inert reservation, verify cancellation and crash
holds before connecting Unity. Extends the controller queue design in
../specs/2026-09-17-controller-queue.md. Python 3.11+ standard library only.

The worker requires an explicitly selected existing database. It claims at most
one FIFO request, commits before waiting, checks Stop every 100 ms, and releases
after the bounded wait stops. It emits only request ID, mode, outcome and elapsed
time; never reservation tokens, prompt text, or target/account data. It has no
network, model, Unity, computer, arbitrary command or callback action adapter.
Wait duration is finite, 0 to 60 seconds. SQLite operations use a bounded timeout.

A stopped run releases as cancelled; a normal inert wait releases as released,
which is not a QA pass. Busy and empty queues return distinct results. Unexpected
errors or process death after acquisition leave ownership held. There is no
automatic lease expiry/reclaim, replay, restart loop or scheduled worker. A fresh
worker seeing a held slot returns blocked, never resets it. Crash recovery here
means safe persistence, not restoration of a lost owner token.

- [x] Add tests/test_farmqa_worker.py using real temporary SQLite and actual worker
  subprocesses. Verify timed completion, signed Stop, second-session progress,
  abrupt process termination/restart hold, redacted output, no queue/schema
  initialization on missing DB, invalid duration rejection and idle/busy results.
- [x] Run tests before implementation and observe missing worker failure.
- [x] Add tools/farmqa_worker.py: run_once(db_path, seconds), CLI --db and --seconds;
  opening mode=rw prevents accidental database creation. Default wait is 5 seconds.
  Keep all SQLite transactions outside waiting and flush acquisition output for
  supervision. No recovery command and no action capability.
- [x] Run focused and full suites; obtain independent review. Fix concrete findings.
- [x] Save redacted process-run evidence and instructions. Commit locally on
  codex/farmqa-inert-worker. Leave the live receiver and its queue unchanged;
  availability of a standalone operator utility requires no service restart.
