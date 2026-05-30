"""Smoke test: the whole turn pipeline runs end-to-end, offline, without crashing.

This is the green-build gate every teammate runs before pushing:

    pytest -q                 # or just:  python tests/test_smoke.py

It drives a real `GuardianAgent` turn with a scripted `FakeLLM` — no network, no
API key, no database, no DGX Spark. It exercises the path that actually ships:
hybrid router -> specialist node -> tool-calling loop -> tool execution.
"""
from __future__ import annotations

import os
import sys

# Allow `python tests/test_smoke.py` (not just pytest) by putting the repo on path.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.agents.guardian import GuardianAgent
from backend.llm.base import LLMResponse, ToolCall
from backend.tools import build_default_registry
from tests.fakes import FakeLLM


def test_safety_turn_runs_end_to_end() -> None:
    """A clear emergency must route to safety (deterministic keyword fast-path),
    run the tool loop, fire call_911, and return a spoken reply — all offline."""
    # Script the safety specialist: first ask to call 911, then speak a reply.
    llm = FakeLLM(
        [
            LLMResponse(
                text=None,
                tool_calls=[
                    ToolCall(id="t1", name="call_911",
                             arguments={"reason": "fall with chest tightness"})
                ],
            ),
            LLMResponse(text="Stay calm, Eleanor — help is on the way."),
        ]
    )
    guardian = GuardianAgent(llm=llm, registry=build_default_registry())

    result = guardian.turn("I fell and my chest feels tight")

    assert result["route"] == "safety", result
    assert result["reply"].strip(), "specialist must return a spoken reply"
    tools_fired = [c["tool"] for c in result["tool_calls"]]
    assert "call_911" in tools_fired, tools_fired

    # The keyword fast-path must NOT have consulted the model for routing — the
    # only model calls should be the specialist's two scripted turns.
    assert len(llm.calls) == 2, llm.calls


if __name__ == "__main__":
    test_safety_turn_runs_end_to_end()
    print("smoke test passed")
