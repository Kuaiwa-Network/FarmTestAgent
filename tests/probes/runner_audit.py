"""Bounded offline probes of the existing client runner; never starts a game/broker.

Exit 1 means an unsafe acceptance was reproduced, not that this probe crashed.
All account names and slots here are synthetic fixtures.
"""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
client = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("farm_qa_run", client / "tools/device-mcp/qa_run.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StubRunner(module.Runner):
    def __init__(self, outdir):
        super().__init__({"account": "requested-synthetic-account", "server": "requested-synthetic-server"}, outdir)
        self.calls = []

    async def call(self, tool, **args):
        self.calls.append({"tool": tool, "arguments": args})
        if tool == "get_active_views":
            return json.dumps({"CurrentViewTypeName": "MainView"})
        if tool == "mark_console":
            return "0"
        if tool == "dump_model":
            return json.dumps([{}])
        if tool == "water":
            return "true"
        raise AssertionError(f"Unexpected offline call: {tool}")

    async def jslots(self):
        return {7: {"cropId": 0, "watered": False, "harvestTime": 0}}


async def main():
    checks = []
    with tempfile.TemporaryDirectory(prefix="farm-runner-audit-") as outdir:
        runner = StubRunner(outdir)
        result = await runner.step("login")
        checks.append({"id": "RUNNER-IDENTITY", "status": "FAIL", "expected": "Require observed matching account AND server before accepting MainView", "actual": result, "calls": runner.calls.copy()})
        runner.calls.clear()
        result = await runner.step("water 7")
        checks.append({"id": "RUNNER-EMPTY-WATER", "status": "FAIL", "expected": "Reject an empty plot as proof of successful watering", "actual": result, "fixture": await runner.jslots(), "calls": runner.calls.copy()})
        runner.calls.clear()
        result = await runner.crop_count(20001)
        checks.append({"id": "RUNNER-MISSING-OBSERVATION", "status": "FAIL" if result == 0 else "INCONCLUSIVE", "expected": "Unreadable crop records must not become a valid zero baseline", "actual": result, "fixture": [{}], "calls": runner.calls.copy()})
        try:
            await runner.step("click btnWater")
        except SystemExit as exc:
            checks.append({"id": "RUNNER-POINTER", "status": "BLOCKED", "actual": str(exc), "expected": "Pointer-capable replay required for interaction coverage"})
    scenarios = []
    for path in sorted((client / "tests/scenarios").rglob("*.md")):
        try:
            _, steps, _ = module.parse_scenario(path)
            scenarios.append({"path": str(path.relative_to(client)), "parseable": True, "steps": steps})
        except SystemExit as exc:
            scenarios.append({"path": str(path.relative_to(client)), "parseable": False, "reason": str(exc)})
    print(json.dumps({"kind": "OFFLINE_SYNTHETIC_RUNNER_AUDIT", "client": str(client), "checks": checks, "scenario_compatibility": scenarios}, indent=2))
    return 1 if any(c["status"] == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
