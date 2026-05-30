"""Phase 0 — Guardian orchestrator.

Classifies each message and routes to one of five specialist agents.
Phase 2 replaces the LLM router with a LangGraph graph.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv
from openai import OpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai

from backend.agents.safety import SafetyAgent
from backend.agents.companion import CompanionAgent
from backend.agents.reminder import ReminderAgent
from backend.agents.behavior import BehaviorAgent
from backend.agents.caregiver_liaison import CaregiverLiaisonAgent
from backend.agents.health import HealthAgent

load_dotenv()

_ROUTER_PROMPT = """\
You are a triage router for a home-care AI companion.
Classify the patient message as exactly one of:

  safety    — fall, chest pain, difficulty breathing, severe pain, or any
              situation needing immediate emergency help.
  reminder  — medication reminders, appointment questions, daily schedule.
  behavior  — mood shifts, withdrawal, confusion, sleep or appetite changes,
              long-term behavioural patterns.
  caregiver — contacting family, sending a message to Maria, sharing an update
              with the care team or doctor.
  health    — symptoms, vitals, medication questions, chronic condition
              questions, general health advice.
  companion — everything else: conversation, memory, general wellbeing,
              emotional support.

Reply with exactly one word from the list above.
"""

_ROUTES = {"safety", "reminder", "behavior", "caregiver", "health", "companion"}


class GuardianAgent:
    def __init__(self) -> None:
        self._client = wrap_openai(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self._history: list[dict[str, str]] = []
        self._agents = {
            "safety": SafetyAgent(self._client, self._model),
            "companion": CompanionAgent(self._client, self._model),
            "reminder": ReminderAgent(self._client, self._model),
            "behavior": BehaviorAgent(self._client, self._model),
            "caregiver": CaregiverLiaisonAgent(self._client, self._model),
            "health": HealthAgent(self._client, self._model),
        }

    @traceable(name="guardian-router")
    def _route(self, message: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _ROUTER_PROMPT},
                {"role": "user", "content": message},
            ],
            max_tokens=5,
        )
        label = response.choices[0].message.content.strip().lower()
        for route in _ROUTES:
            if route in label:
                return route
        return "companion"

    @traceable(name="guardian-orchestrator")
    def chat(self, user_message: str) -> str:
        route = self._route(user_message)
        reply = self._agents[route].chat(user_message, self._history)
        self._history.append({"role": "user", "content": user_message})
        self._history.append({"role": "assistant", "content": reply})
        return reply
