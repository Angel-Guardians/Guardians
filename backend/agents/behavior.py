from __future__ import annotations

from backend.agents.base import ToolCallingAgent
from backend.agents.prompts import get_prompt


class BehaviorAgent(ToolCallingAgent):
    name = "behavior"
    system_prompt = get_prompt("behavior")
    # Flags concerns to the patient's emergency contact via notify_caregiver (the
    # number is looked up from the DB) — matches the behavior prompt's instruction.
    tool_names = ("notify_caregiver", "recall_history")
    voice_profile = "firm"
    escalation_ceiling = "tier_2_nudge"
