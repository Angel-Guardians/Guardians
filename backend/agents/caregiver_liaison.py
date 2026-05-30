from __future__ import annotations

from backend.agents.base import ToolCallingAgent
from backend.agents.prompts import get_prompt


class CaregiverLiaisonAgent(ToolCallingAgent):
    name = "caregiver"
    system_prompt = get_prompt("caregiver")
    tool_names = ("notify_caregiver", "recall_history")
    voice_profile = "formal"
    escalation_ceiling = "tier_3_alarm"
