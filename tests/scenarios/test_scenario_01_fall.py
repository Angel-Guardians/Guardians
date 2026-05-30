"""Scenario 1 - Midnight fall (Eleanor), text-mode end-to-end.

Feeds the fall transcript through the real GuardianAgent orchestrator with a
scripted FakeLLM (no network). Proves the full Phase-1 flow:
    router -> safety agent -> call_911 stub -> notify_caregiver stub -> spoken reply
"""
from __future__ import annotations

from pathlib import Path

from backend.agents.guardian import GuardianAgent
from backend.llm.base import LLMResponse, ToolCall
from backend.tools import build_default_registry
from backend.tools import emergency
from tests.fakes import FakeLLM

TRANSCRIPT = Path(__file__).parent / "test_elenor.txt"


def test_scenario_01_fall_e2e() -> None:
    emergency.CALL_LOG.clear()

    # Scripted model behaviour for the safety agent: first emit both emergency
    # tool calls, then (after the stubs return) compose a calm spoken reply.
    scripted = [
        LLMResponse(
            text=None,
            tool_calls=[
                ToolCall(id="c1", name="call_911",
                         arguments={"reason": "fall with chest tightness", "location": "home"}),
                ToolCall(id="c2", name="notify_caregiver",
                         arguments={"message": "Eleanor fell and EMS is on the way.",
                                    "contact": "Maria"}),
            ],
            finish_reason="tool_calls",
        ),
        LLMResponse(text="Help is on the way, Eleanor. I'm staying right here with you."),
    ]
    llm = FakeLLM(scripted)
    guardian = GuardianAgent(llm=llm, registry=build_default_registry())

    message = TRANSCRIPT.read_text(encoding="utf-8")
    reply = guardian.chat(message)

    # 1. Routed to safety via the deterministic keyword path (no model call to route).
    assert guardian.route(message) == "safety"

    # 2. The call_911 stub actually fired, with the patient context passed through.
    dispatched = [e for e in emergency.CALL_LOG if e["tool"] == "call_911"]
    assert len(dispatched) == 1
    assert dispatched[0]["status"] == "dispatched"

    # 3. The caregiver was notified.
    notified = [e for e in emergency.CALL_LOG if e["tool"] == "notify_caregiver"]
    assert len(notified) == 1
    assert notified[0]["contact"] == "Maria"

    # 4. The agent returned a final spoken reassurance, not a raw tool payload.
    assert "help is on the way" in reply.lower()
