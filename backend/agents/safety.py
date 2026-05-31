from __future__ import annotations

from backend.agents.base import ToolCallingAgent
from backend.agents.prompts import get_prompt


class SafetyAgent(ToolCallingAgent):
    name = "safety"
    system_prompt = get_prompt("safety")
    # Safety is the only agent that can reach emergency dispatch. It holds the full
    # outbound action set: 911, the caregiver, an arbitrary contact (e.g. a
    # neighbour), and the cool-space lookup for heat emergencies.
    tool_names = ("call_911", "notify_caregiver", "call_person", "find_cool_space")
    voice_profile = "urgent"
    escalation_ceiling = "tier_4_call"
