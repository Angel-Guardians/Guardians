"""Tier 2 - the six specialist sub-agents.

  Safety            - falls, panic, violence, immediate danger
  Health            - vitals, anomalies, chronic
  Reminder          - meds, vitamins, appointments
  Companion         - talk, calm, recall
  Behavior          - long-horizon behavioural monitoring
  CaregiverLiaison  - reports / share / loop in humans

Each sub-agent is a LangGraph subgraph with its own system prompt, its
own allowed tool subset, its own voice profile, and its own escalation
ceiling. They all share the same backing Llama 3.1 8B model.
"""

from backend.agents.base import SubAgent
from backend.agents.behavior import BehaviorAgent
from backend.agents.caregiver_liaison import CaregiverLiaisonAgent
from backend.agents.companion import CompanionAgent
from backend.agents.health import HealthAgent
from backend.agents.reminder import ReminderAgent
from backend.agents.safety import SafetyAgent

ALL_AGENT_CLASSES: list[type[SubAgent]] = [
    SafetyAgent,
    HealthAgent,
    ReminderAgent,
    CompanionAgent,
    BehaviorAgent,
    CaregiverLiaisonAgent,
]

__all__ = [
    "SubAgent",
    "SafetyAgent",
    "HealthAgent",
    "ReminderAgent",
    "CompanionAgent",
    "BehaviorAgent",
    "CaregiverLiaisonAgent",
    "ALL_AGENT_CLASSES",
]
