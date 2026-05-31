from __future__ import annotations

from backend.agents.base import ToolCallingAgent
from backend.agents.prompts import get_prompt


class SafetyAgent(ToolCallingAgent):
    name = "safety"
    system_prompt = get_prompt("safety")
    # Safety is the only agent that can reach emergency dispatch. Its action set is
    # the emergency line (call_911), the patient's caregivers (notify_caregiver), and
    # an arbitrary contact such as a neighbour (call_person).
    tool_names = ("call_911", "notify_caregiver", "call_person")
    voice_profile = "urgent"
    escalation_ceiling = "tier_4_call"
