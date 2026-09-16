# Observation and runner regressions

Source/build: client 688da4652; verified 2026-09-16. These are bounded infrastructure
reproductions, not gameplay. Existing client implementation is read-only.

## QA-001: serializer retains properties

Execute `tests/probes/serializer-probe.cs.txt` through Unity `execute_code` while idle.
It constructs synthetic objects only. Required behavior: semantic slot/crop fields
retain values in the dump, including explicit default values in the eventual QA schema.
Observed: typed slot `[7,20001,true,1234567890]` → `{}`, dictionary →
`[{"k":7,"v":{}}]`; typed crop `[20001,4]` → `[{}]`. **FAIL**.
Retest via the actual new driver snapshot when the developer fixes QA-001; testing
only a replacement general serializer would not prove the driver uses it.

## QA-002/003/004: runner acceptance

```sh
python3 tests/probes/runner_audit.py /Users/elendil/WorkSpaces/Farm/Farm-Client
```

The probe replaces transport/state reads with explicitly synthetic fixtures, never
starts the broker and makes no real requests. Its exit 1 denotes reproduced unsafe
acceptance; current output is a diagnostic, not a general future green-test runner.
After a fix, adapt transport stubs to the new observation contract while preserving
the expected behavior below; never simply change the assertions to match the client.

- MainView without authenticated matching account/server must not report requested
  login success. Currently returns the requested account/server without reading either.
- Empty plot with `cropId=0, watered=false, harvestTime=0` must not report watering success.
  Currently reports `slot 7 watered` after the mocked request.
- Crop payload `[{}]` must be unknown/error, not count 0. Currently returns 0.

All three failures reproduced twice; JSON evidence retained. The same probe reports
unsupported `click btnWater` and parser compatibility (1/4 documents). Those are
capability checks, not simulated interactions or product failures.
