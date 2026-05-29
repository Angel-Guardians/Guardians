"""Safety Agent.

Owns anything where the failure mode is physical harm in the next 60s:
falls, panic phrases, breaking glass, the silent-morning case, choking,
fire. The only sub-agent allowed to trigger 911 directly.

Escalation ceiling: 911 + family contact.
Voice profile: URGENT.

Scenarios primarily owned: 1, 2, 9, 12, 14, 16, 20, 21, 24.
"""
from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from backend.agents.base import SubAgent
from backend.agents.voice_profiles import VoiceProfile

if TYPE_CHECKING:
    from langgraph.graph import StateGraph


class SafetyAgent(SubAgent):
    name: ClassVar[str] = "safety"
    voice_profile: ClassVar[VoiceProfile] = VoiceProfile.URGENT
    escalation_ceiling: ClassVar[str] = "911+family"
    allowed_tools: ClassVar[set[str]] = {
        "emergency_caller",
        "contact_tree",
        "geolocation",
        "ambient_lights",
        "tts",
        "notification_dispatcher",
        "audio_listener",
        "vision_motion",
        "event_log_write",
        "event_log_query",
    }

    def build_graph(self) -> "StateGraph":
        # TODO: assess -> dispatch -> stay-with-patient subgraph
        raise NotImplementedError("Day 1 PM")
