"""Health Agent.

Owns vitals, anomalies, chronic-condition signals, structured medical
differentials. Time horizon: minutes to days. Cannot dispatch 911
directly - hands off to Safety via HandoffEvent for Tier 4.

Escalation ceiling: clinician note / urgent-care suggestion.
Voice profile: CALM.

Scenarios primarily owned: 4, 11, 13, 25. Frequently spawned alongside
others in 1, 12, 14, 16, 21.
"""
from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from backend.agents.base import SubAgent
from backend.agents.voice_profiles import VoiceProfile

if TYPE_CHECKING:
    from langgraph.graph import StateGraph


class HealthAgent(SubAgent):
    name: ClassVar[str] = "health"
    voice_profile: ClassVar[VoiceProfile] = VoiceProfile.CALM
    escalation_ceiling: ClassVar[str] = "clinician_note"
    allowed_tools: ClassVar[set[str]] = {
        "bio_marker",
        "personal_baseline",
        "anomaly_detector",
        "interaction_check",
        "medical_rag",
        "clinical_consult",
        "tts",
        "notification_dispatcher",
        "event_log_query",
        "event_log_write",
    }

    def build_graph(self) -> "StateGraph":
        # TODO: vitals-window-pull -> baseline-compare -> classify -> respond
        raise NotImplementedError("Day 3 AM")
