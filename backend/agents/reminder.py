"""Reminder Agent.

Owns medication and supplement schedules, refills, appointments.
Handles substance-interaction logic (iron vs calcium, metformin with
food). Most reminders are scheduled, not user-initiated.

Escalation ceiling: caregiver heads-up after N missed doses.
Voice profile: GENTLE.

Scenarios primarily owned: 3 (Sarah). Active in 4, 5, 16, 19, 23, 25.
"""
from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from backend.agents.base import SubAgent
from backend.agents.voice_profiles import VoiceProfile

if TYPE_CHECKING:
    from langgraph.graph import StateGraph


class ReminderAgent(SubAgent):
    name: ClassVar[str] = "reminder"
    voice_profile: ClassVar[VoiceProfile] = VoiceProfile.GENTLE
    escalation_ceiling: ClassVar[str] = "caregiver_heads_up"
    allowed_tools: ClassVar[set[str]] = {
        "regimen_store",
        "interaction_check",
        "notification_dispatcher",
        "tap_confirm",
        "ui_renderer",
        "calendar_mcp",
        "pharmacy",
        "tts",
        "event_log_write",
        "event_log_query",
    }

    def build_graph(self) -> "StateGraph":
        # TODO: schedule-tick -> regimen-read -> conflict-check -> dispatch
        raise NotImplementedError("Day 2 AM")
