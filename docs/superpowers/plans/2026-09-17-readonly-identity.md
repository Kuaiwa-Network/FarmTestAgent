# Read-only target identity implementation plan

> Execute inline with superpowers:executing-plans and test-driven-development;
> request an independent review before committing.

**Goal:** collect current Editor identity for an existing controller request and
persist a conservative comparison without acquiring or releasing its reservation.

**Architecture:** a small standard-library client reads the existing loopback
Unity MCP service and runs the existing fixed in-memory readiness probe. A
separate checker reads the request's immutable target, inspects local Git before
and after, and appends allowlisted diagnostics to the same private ledger.

**Spec:** [approved architecture](../../farmqa-architecture.md), first gameplay gate.
Python 3.11+, standard library only. No client edits, game code invocation, Play
Mode, automatic enqueue, secrets, deployment changes, or gameplay execution.

## Evidence-driven scope

Live inspection found one idle Windows Editor at the expected client path,
four dirty/untracked files, and loaded module IDs. No loaded-commit provenance
was found in the inspected source/probe. Play Mode is off, so there is no observed
connected server session. These are explicit unknown checks, never inferred from
Git, assembly timestamps, requested environment, or a caller-provided assertion.

This version always returns BLOCKED for gameplay. It can positively compare
instance/project, requested build target, source commit, clean/stable checkout,
and presence of expected loaded assemblies. It cannot issue an execution permit.
Platform and instance are explicit operator arguments because the existing target
schema does not yet pin them. Store these expectations with each observation.

## Steps

- [x] Add `tests/test_farmqa_identity.py`: real temporary Git and SQLite; fake
  external Unity responses only. Catch mismatched instance/project/platform/SHA,
  dirty or changing source, stale/malformed state, missing assemblies, unsafe
  Editor state, missing/cancelled request and accidental reservation changes.
  Verify `python -m unittest discover -s tests -p test_farmqa_identity.py -v`
  fails before implementing the new module.
- [x] Add `tools/farmqa_unity_identity.py`: loopback-only MCP HTTP, bounded
  JSON/SSE responses, request/response ID checks, no redirects/proxies or retries;
  fixed resource reads, explicit instance selection and fixed readiness probe.
  Add wire tests with a local HTTP fixture for framing, errors and URL rejection.
- [x] Add `tools/farmqa_identity.py`: `inspect_request(db_path, request_id,
  instance, build_target, client)`; current state before/after probe, Git snapshot
  before/after; fail closed; append `controller_identity_observations` inside a
  short transaction and recheck request state/target before recording. No lock
  spans network calls. No old observation is accepted as an input or permit.
- [x] Run tests, then the CLI on a private synthetic request against the live
  Editor. Confirm persisted BLOCKED diagnostics, unchanged reservation and client
  dirty-file hashes. Do not consume or retarget a production event.
- [x] Update architecture, operator guide, topic knowledge, dated report and
  redacted evidence. Request independent review, fix concrete findings, run the
  full Python suite and `git diff --check`, and commit locally. No push yet.
