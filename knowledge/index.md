# Knowledge index

Read `../CLAUDE.md` first. Last updated: 2026-09-17.

- [FarmQA architecture and durable memory](../docs/farmqa-architecture.md) —
  consolidated design reference; implemented, verified, and planned behavior

- [Infrastructure and verified limits](infrastructure.md)
- [Planting gameplay guide](gameplay/planting.md) — source-grounded; no live journey yet
- [Execution/evidence procedure](procedures/interaction-runs.md)
- [Open issues and next steps](issues.md)
- [Verified lessons and candidate lessons](lessons/learning-log.md)
- [Coverage and improvement measurements](metrics.md)
- [FarmQA Linear integration](linear-farmqa.md) — activated; live mention and follow-up verified
- [Gameplay infrastructure report](../reports/2026-09-16-initial-learning/report.md)
- [Latest: FarmQA mention implementation](../reports/2026-09-16-farmqa-hello/report.md)
- [Windows FarmQA deployment](../reports/2026-09-16-farmqa-windows/report.md) — fresh
  tunnel and Windows fixes; consult this report for current activation evidence
- [FarmQA Codex desktop bridge](../reports/2026-09-16-farmqa-codex-bridge/report.md)
  — live Linear → Codex app → Linear delivery verified; remaining limits recorded
- [Latest: bridge follow-up preflight and Windows gameplay readiness](../reports/2026-09-16-farmqa-followup-preflight/report.md)
  — fresh Linear session and follow-up both PASS; Editor installed but stopped
- [FarmQA Stop handling](../reports/2026-09-16-farmqa-stop/report.md)
  — queued cancellation/reply suppression deployed; automatic active-task interruption blocked
- [Windows Unity read-only readiness](../reports/2026-09-16-unity-readiness/report.md)
  — Editor connection, loaded assembly identity, Console, and screenshots verified;
  Play Mode off and gameplay still disabled
- [FarmQA manual Stop verification](../reports/2026-09-16-farmqa-manual-stop/report.md)
  — exact Codex turn interrupted by the user; ordinary reply suppressed and
  follow-up visibly delivered; automatic interruption still unavailable
- [FarmQA automatic Stop capability check](../reports/2026-09-16-farmqa-automatic-stop-capability/report.md)
  — documented interrupt protocol cannot reach the existing desktop inbox
- [FarmQA session routing and target snapshots](../reports/2026-09-16-farmqa-sessions/report.md)
  — distinct conversations and follow-up context after restart verified; empty-item reader fallback deployed
- [FarmQA controller reservation queue](../reports/2026-09-17-farmqa-controller/report.md)
  — persistent FIFO ownership and Stop integration; no game-action worker enabled
- [FarmQA inert worker](../reports/2026-09-17-farmqa-inert-worker/report.md)
  — real process tests verify inert cancellation and crash holds; no gameplay
- [FarmQA read-only identity diagnostics](../reports/2026-09-17-farmqa-identity/report.md)
  — request-bound live Editor/source comparison; loaded provenance and server
  identity remain unknown, so gameplay stays BLOCKED
- [FarmQA provenance and session-source investigation](../reports/2026-09-17-farmqa-provenance/report.md)
  — compiled source checksums correspond; complete build provenance still needs
  a controlled build, and no server session has been observed
- [FarmQA isolated controlled build](../reports/2026-09-17-farmqa-controlled-build/report.md)
  — Editor compilation and four loaded module matches verified; tracked import
  drift blocks clean provenance, Play Mode off and original checkout preserved

Current request: forward **@FarmQA** messages into a Codex desktop task and return
the task's final reply to Linear. The fixed-reply connection test passed. Gameplay
priority remains: resolve trustworthy observation and identity gaps; then perform
supervised Editor learning, repeat, and Android replay. Infrastructure-first user
correction is recorded; do not start by repeating the account question.
