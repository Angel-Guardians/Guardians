"""Companion Agent.

Owns conversation, calm-keeping, memory recall, mood check-ins.
Holds the TTS lock during most active dialogue. Cannot call 911;
escalates to Safety via HandoffEvent on red flags.

Escalation ceiling: hand off to Health / Safety.
Voice profile: CALM (or CLONED for some patients).

Scenarios primarily owned: 5, 6. Spawned in parallel with Safety in
every Tier-4 incident.
"""
from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from backend.agents.base import SubAgent
from backend.agents.voice_profiles import VoiceProfile

if TYPE_CHECKING:
    from langgraph.graph import StateGraph


class CompanionAgent(SubAgent):
    name: ClassVar[str] = "companion"
    voice_profile: ClassVar[VoiceProfile] = VoiceProfile.CALM
    escalation_ceiling: ClassVar[str] = "handoff_to_safety_or_health"
    allowed_tools: ClassVar[set[str]] = {
        "tts",
        "conversation_memory",
        "event_log_query",
        "event_log_write",
        "spotify_mcp",
        "ambient_lights",
        "tap_confirm",
    }

    def build_graph(self) -> "StateGraph":
        # TODO: listen -> classify intent -> {answer-from-memory | grounding | recap}
        raise NotImplementedError("Day 1 PM")
