from __future__ import annotations

from backend.agents.base import ToolCallingAgent
from backend.agents.prompts import get_prompt


class SafetyAgent(ToolCallingAgent):
    name = "safety"
    system_prompt = get_prompt("safety")
    # Safety is the only agent that can reach emergency dispatch. It calls 911 and
    # notifies the caregiver (whose number is looked up from the DB by name), plus
    # the cool-space lookup for heat emergencies. `call_person` is intentionally
    # NOT bound: it takes a raw phone number, which the model would hallucinate —
    # caregiver calls must go through notify_caregiver so the number comes from the DB.
    tool_names = ("call_911", "notify_caregiver", "find_cool_space")
    voice_profile = "urgent"
    escalation_ceiling = "tier_4_call"
