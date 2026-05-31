"""Guardian orchestrator (LangGraph).

Orchestration is a compiled LangGraph `StateGraph` (see backend/agents/graph.py).
A hybrid router node — deterministic keyword fast-path for true emergencies, LLM
classification for everything else — selects one of six specialist nodes via
conditional edges. Every node talks only to the `backend.llm` interface, so the
graph runs unchanged on OpenAI cloud or a local DGX Spark endpoint.

Observability: with LANGSMITH_TRACING=true and LANGSMITH_API_KEY set, LangGraph
traces each turn to LangSmith — one span per node, model calls nested beneath.
"""
from __future__ import annotations

from backend.agents.behavior import BehaviorAgent
from backend.agents.caregiver_liaison import CaregiverLiaisonAgent
from backend.agents.companion import CompanionAgent
from backend.agents.graph import build_guardian_graph
from backend.agents.health import HealthAgent
from backend.agents.reminder import ReminderAgent
from backend.agents.safety import SafetyAgent
from backend.llm import LLMClient, Message, build_llm
from backend.llm.tracing import trace
from backend.tools import ToolRegistry, build_default_registry

_ROUTES = ("safety", "reminder", "behavior", "caregiver", "health", "companion")

# Deterministic safety net: if any of these appear, route to safety without asking
# the model. Cheap insurance against a misclassification on the one path that matters.
_SAFETY_KEYWORDS = (
    "fell",
    "fallen",
    "can't get up",
    "cant get up",
    "chest pain",
    "chest feels tight",
    "can't breathe",
    "cant breathe",
    "difficulty breathing",
    "trouble breathing",
    "unconscious",
    "not breathing",
    "bleeding",
    "stroke",
    "help me",
)

_ROUTER_PROMPT = """\
You are the triage router for a home-care AI companion that supports a person
living alone. Read the person's message and reply with exactly ONE category word.

The most important job is to catch emergencies. When in doubt between safety and
anything else, choose safety.

Categories:
  safety    — emergencies or physical danger: a fall, chest pain, trouble
              breathing, severe pain, bleeding, fainting, a racing or pounding
              irregular heartbeat, feeling like something is very wrong, or
              "I'm dying". Anything that may need immediate help.
  reminder  — a specific question about medication timing, appointments, or the
              daily schedule ("did I take my pills?", "when is my appointment?").
  caregiver — an explicit request to contact or message family or a caregiver
              ("tell my sister I'm okay", "let my daughter know").
  health    — a specific NON-emergency symptom or vital reading ("my knee aches",
              "what was my blood pressure last week?").
  companion — the default. Ordinary conversation, company, emotional support,
              loneliness, mood, encouragement, and short replies ("yes", "no",
              "done", "good morning", "I've been feeling lonely").

Rules:
- Reply with exactly ONE word from the list. No punctuation, no explanation.
- companion is the home base: if the message is just conversation, feelings, or a
  short reply, choose companion.
- But emergencies ALWAYS win. Any sign of physical danger or alarming symptoms
  goes to safety, never companion.

Examples:
  "I fell and I can't get up" -> safety
  "My chest feels tight and I can't breathe" -> safety
  "I think I'm dying" -> safety
  "I feel dizzy and my heart is racing" -> safety
  "Did I already take my morning pills?" -> reminder
  "Can you let my sister know I'm okay?" -> caregiver
  "Good morning, it's a lovely day" -> companion
  "I've been feeling a bit lonely lately" -> companion
  "Yes, that sounds good" -> companion

Classify the next message. Reply with exactly one word.
"""


class GuardianAgent:
    def __init__(
        self,
        llm: LLMClient | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        # Single integration point: build the client once and inject it everywhere.
        self._llm = llm or build_llm()
        self._registry = registry or build_default_registry()
        self._history: list[Message] = []
        self._agents = {
            "safety": SafetyAgent(self._llm, self._registry),
            "companion": CompanionAgent(self._llm, self._registry),
            "reminder": ReminderAgent(self._llm, self._registry),
            "behavior": BehaviorAgent(self._llm, self._registry),
            "caregiver": CaregiverLiaisonAgent(self._llm, self._registry),
            "health": HealthAgent(self._llm, self._registry),
        }
        # Compile the LangGraph orchestrator once.
        self._graph = build_guardian_graph(self.route, self._agents)

    @trace(name="guardian-router")
    def route(self, message: str) -> str:
        lowered = message.lower()
        if any(kw in lowered for kw in _SAFETY_KEYWORDS):
            return "safety"

        response = self._llm.chat(
            [
                Message(role="system", content=_ROUTER_PROMPT),
                Message(role="user", content=message),
            ],
            max_tokens=24,
            temperature=0.0,
        )
        label = (response.text or "").strip().lower()
        for route in _ROUTES:
            if route in label:
                return route
        return "companion"

    def reset(self) -> None:
        """Wipe the conversation memory so tests can be reproduced from a clean slate.

        Clears the in-process history shared across all specialists. The next turn
        starts as if the backend had just booted (no prior context).
        """
        self._history.clear()

    def chat(self, user_message: str) -> str:
        return self.turn(user_message)["reply"]

    def turn(self, user_message: str) -> dict:
        """One full turn. Returns {route, reply, tool_calls}.

        Tool calls are captured from the per-module audit logs the stubs append to
        (see backend/tools/*). The API layer turns this dict into bus events so the
        Live page shows which specialist ran and which tools fired.
        """
        from backend.tools import emergency, health, reminder

        logs = (emergency.CALL_LOG, health.CALL_LOG, reminder.CALL_LOG)
        for log in logs:
            log.clear()

        # Invoke the compiled graph for this turn. LangGraph traces the run to
        # LangSmith automatically when tracing env vars are set.
        result = self._graph.invoke(
            {"user_message": user_message, "history": list(self._history)},
            config={"run_name": "guardian-turn"},
        )
        reply = result["reply"]
        route = result.get("route", "companion")
        self._history.append(Message(role="user", content=user_message))
        self._history.append(Message(role="assistant", content=reply))

        tool_calls = [dict(e) for log in logs for e in log]
        return {"route": route, "reply": reply, "tool_calls": tool_calls}
