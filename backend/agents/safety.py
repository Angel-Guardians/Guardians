from __future__ import annotations

from backend.agents.base import ToolCallingAgent
from backend.agents.prompts import get_prompt


class SafetyAgent(ToolCallingAgent):
    name = "safety"
    system_prompt = get_prompt("safety")
    tool_names = ("call_person", "find_cool_space")
    voice_profile = "urgent"
    escalation_ceiling = "tier_4_call"
