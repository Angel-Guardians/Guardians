from __future__ import annotations

from backend.agents.base import ToolCallingAgent
from backend.agents.prompts import get_prompt


class HealthAgent(ToolCallingAgent):
    name = "health"
    system_prompt = get_prompt("health")
    tool_names = ("log_vital", "get_medications", "recall_history")
    voice_profile = "calm"
    escalation_ceiling = "tier_3_alarm"
