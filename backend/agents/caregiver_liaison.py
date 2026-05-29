"""Caregiver Liaison Agent.

The only sub-agent that talks to OTHER HUMANS: doctors, family,
counselors, probation officers, paramedics. Centralizes the consent
model. Produces the weekly clinical summary, counselor notes, and
incident reports.

Does NOT call 911 in-home (that's Safety). Does push structured
incident summaries to receiving hospitals via FHIR.

Escalation ceiling: outbound to humans only - no in-home escalation.
Voice profile: FORMAL.

Scenarios primarily owned: 4 (note to Dr Patel), 18, 19, 27.
Active in nearly every Tier-3+ incident as the follow-up tail.
"""
from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from backend.agents.base import SubAgent
from backend.agents.voice_profiles import VoiceProfile

if TYPE_CHECKING:
    from langgraph.graph import StateGraph


class CaregiverLiaisonAgent(SubAgent):
    name: ClassVar[str] = "caregiver_liaison"
    voice_profile: ClassVar[VoiceProfile] = VoiceProfile.FORMAL
    escalation_ceiling: ClassVar[str] = "outbound_only"
    allowed_tools: ClassVar[set[str]] = {
        "contact_tree",
        "twilio_comms",
        "fhir_share",
        "counselor_portal",
        "calendar_mcp",
        "event_log_query",
        "event_log_write",
        "ui_renderer",
        "tts",
    }

    def build_graph(self) -> "StateGraph":
        # TODO: incident-summary -> consent-check -> recipient-routing -> dispatch
        raise NotImplementedError("Day 3 PM")
