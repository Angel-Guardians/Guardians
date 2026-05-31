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
You are a triage router for a home-care AI companion.
Classify the patient message as exactly one of:

  safety    — fall, chest pain, difficulty breathing, severe pain, or any
              situation needing immediate emergency help.
  reminder  — medication reminders, appointment questions, daily schedule.
  behavior  — mood shifts, withdrawal, confusion, sleep or appetite changes.
  caregiver — contacting family, sending a message to Maria, sharing an update.
  health    — symptoms, vitals, medication questions, chronic conditions.
  companion — everything else: conversation, memory, emotional support.

Reply with exactly one word from the list above.
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
        self._last_route: str = "companion"
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
    def route(self, message: str, history: list[Message] | None = None) -> str:
        lowered = message.lower()
        if any(kw in lowered for kw in _SAFETY_KEYWORDS):
            return "safety"

        # Include the last 4 messages (2 turns) so the router can classify
        # short replies like "yes" or "maybe" in context.
        context = (history or [])[-4:]
        prior_hint = (
            f"\nThe previous turn was handled by the '{self._last_route}' agent. "
            "If the patient's reply is a short follow-up (e.g. 'yes', 'no', 'maybe', 'sure'), "
            "keep routing to the same agent unless the content clearly belongs elsewhere."
        )
        response = self._llm.chat(
            [
                Message(role="system", content=_ROUTER_PROMPT + prior_hint),
                *context,
                Message(role="user", content=message),
            ],
            max_tokens=8,
            temperature=0.0,
        )
        label = (response.text or "").strip().lower()
        for route in _ROUTES:
            if route in label:
                return route
        return "companion"

    def chat(self, user_message: str) -> str:
        return self.turn(user_message)["reply"]

    def turn(self, user_message: str) -> dict:
        """One full turn. Returns {route, reply, tool_calls}.

        Tool calls are captured from the per-module audit logs the stubs append to
        (see backend/tools/*). The API layer turns this dict into bus events so the
        Live page shows which specialist ran and which tools fired.
        """
        from backend.tools import emergency, general_tools, health, reminder

        logs = (emergency.CALL_LOG, general_tools.CALL_LOG, health.CALL_LOG, reminder.CALL_LOG)
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
        self._last_route = route
        self._history.append(Message(role="user", content=user_message))
        self._history.append(Message(role="assistant", content=reply))

        tool_calls = [dict(e) for log in logs for e in log]
        return {"route": route, "reply": reply, "tool_calls": tool_calls}
