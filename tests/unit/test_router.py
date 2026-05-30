"""Unit tests for the hybrid router."""
from __future__ import annotations

from backend.agents.guardian import GuardianAgent
from backend.llm.base import LLMResponse
from backend.tools import build_default_registry
from tests.fakes import FakeLLM


def test_fall_keyword_routes_to_safety_without_calling_model() -> None:
    """Deterministic fast-path: a fall must reach safety even if the model would
    misclassify. No LLM call should be made for routing."""
    llm = FakeLLM([])  # if the router consulted the model it would be recorded
    guardian = GuardianAgent(llm=llm, registry=build_default_registry())

    route = guardian.route("I fell and I can't get up")

    assert route == "safety"
    assert llm.calls == []  # keyword path short-circuited before any model call


def test_ambiguous_utterance_falls_through_to_llm() -> None:
    """No keyword match -> the LLM classifier decides."""
    llm = FakeLLM([LLMResponse(text="reminder")])
    guardian = GuardianAgent(llm=llm, registry=build_default_registry())

    route = guardian.route("what time do I take my pills again?")

    assert route == "reminder"
    assert len(llm.calls) == 1  # the classifier was consulted
