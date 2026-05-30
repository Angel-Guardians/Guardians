from __future__ import annotations

from backend.agents.base import ToolCallingAgent
from backend.agents.prompts import get_prompt


class ReminderAgent(ToolCallingAgent):
    name = "reminder"
    system_prompt = get_prompt("reminder")
    tool_names = ("get_schedule", "mark_med_taken", "recall_history")
    voice_profile = "gentle"
    escalation_ceiling = "tier_2_nudge"
