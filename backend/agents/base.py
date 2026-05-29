"""SubAgent abstract base.

Each of the six sub-agents extends this. The base owns the shared
machinery: tool gating, voice-profile selection, event-bus subscription.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from backend.agents.voice_profiles import VoiceProfile
from backend.events.types import GuardianEvent

if TYPE_CHECKING:
    from langgraph.graph import StateGraph

    from backend.events.bus import EventBus


class SubAgent(ABC):
    """Base class for every sub-agent.

    Subclasses set these class vars:
      name                : short identifier ("safety", "companion", ...)
      voice_profile       : Kokoro voice ID category
      escalation_ceiling  : human-readable ceiling, e.g. "911+family"
      allowed_tools       : set of tool names this sub-agent can call
    """

    name: ClassVar[str]
    voice_profile: ClassVar[VoiceProfile]
    escalation_ceiling: ClassVar[str]
    allowed_tools: ClassVar[set[str]]

    def __init__(self, bus: "EventBus") -> None:
        self.bus = bus
        self._graph: StateGraph | None = None

    @abstractmethod
    def build_graph(self) -> "StateGraph":
        """Construct the LangGraph subgraph that drives this sub-agent."""

    async def handle(self, event: GuardianEvent) -> None:
        """Invoke the subgraph for an event."""
        if self._graph is None:
            self._graph = self.build_graph()
        # TODO: invoke the compiled graph with event in state
        raise NotImplementedError
