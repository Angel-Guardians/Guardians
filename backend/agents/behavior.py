from __future__ import annotations

from backend.agents.base import ToolCallingAgent
from backend.agents.prompts import get_prompt


class BehaviorAgent(ToolCallingAgent):
    name = "behavior"
    system_prompt = get_prompt("behavior")
    tool_names = ("notify_caregiver", "recall_history")
    voice_profile = "firm"
    escalation_ceiling = "tier_2_nudge"
