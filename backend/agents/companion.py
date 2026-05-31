from __future__ import annotations

from backend.agents.base import ToolCallingAgent
from backend.agents.prompts import get_prompt


class CompanionAgent(ToolCallingAgent):
    name = "companion"
    system_prompt = get_prompt("companion")
    tool_names = ("recall_history",)
    voice_profile = "calm"
    escalation_ceiling = "tier_1_whisper"
