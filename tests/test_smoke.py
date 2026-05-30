"""Smoke test: the whole pipeline runs end-to-end in mock mode without crashing.
Run with:  python -m pytest -q   (or just `python tests/test_smoke.py`)
This is the gate every teammate runs before merging.
"""
import os, sys
os.environ["GUARDIAN_USE_MOCK_LLM"] = "1"          # force mock; no Spark needed
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.orchestrator import Context, handle_event
from backend import simulator


def test_hero_scenario_runs():
    scn = simulator.load_scenario("heat_warning_margaret")
    assert scn is not None, "hero scenario must exist"
    ctx = Context({**scn["persona"], "context": scn["context"]})
    last = None
    for entry in scn["timeline"]:
        ev = simulator.make_event(entry)
        last = handle_event(ctx, ev)
    assert last.orchestrator_decision.risk_level in ("HIGH", "CRITICAL")
    tools_used = [t.tool for t in last.tool_calls]
    assert "find_nearest_open_cool_space" in tools_used
    print("OK — hero scenario ended at risk:", last.orchestrator_decision.risk_level)
    print("    tools:", tools_used)


if __name__ == "__main__":
    test_hero_scenario_runs()
    print("smoke test passed")
