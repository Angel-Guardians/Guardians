"""Behavior Agent.

Owns long-horizon behavioural monitoring: anger management, depression
slide, addiction relapse, domestic-violence escalation, child welfare,
caregiver burnout, sundowning, wandering. Time horizon: days to weeks.

Most Behavior workflows run nightly as background jobs and emit
synthetic events. The agent reacts to those events in real time.

Escalation ceiling: counselor / officer portal. Cannot call 911 -
hands off to Safety.
Voice profile: FIRM.

Scenarios primarily owned: 7, 8, 9, 10, 18, 19, 22, 26.
"""
from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from backend.agents.base import SubAgent
from backend.agents.voice_profiles import VoiceProfile

if TYPE_CHECKING:
    from langgraph.graph import StateGraph


class BehaviorAgent(SubAgent):
    name: ClassVar[str] = "behavior"
    voice_profile: ClassVar[VoiceProfile] = VoiceProfile.FIRM
    escalation_ceiling: ClassVar[str] = "counselor_portal_or_handoff_to_safety"
    allowed_tools: ClassVar[set[str]] = {
        "audio_listener",
        "conversation_memory",
        "personal_baseline",
        "anomaly_detector",
        "pattern_absence",
        "regimen_store",
        "ambient_lights",
        "spotify_mcp",
        "tts",
        "event_log_query",
        "event_log_write",
    }

    def build_graph(self) -> "StateGraph":
        # TODO: pattern-evaluate -> threshold -> {intervene | log | handoff}
        raise NotImplementedError("Day 3 / post-hackathon")
