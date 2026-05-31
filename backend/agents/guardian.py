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

from loguru import logger

from backend.agents.anomaly import AnomalyDetectionAgent
from backend.agents.behavior import BehaviorAgent
from backend.agents.caregiver_liaison import CaregiverLiaisonAgent
from backend.agents.companion import CompanionAgent
from backend.agents.graph import build_guardian_graph
from backend.agents.health import HealthAgent
from backend.agents.input_filter import clean_input
from backend.agents.reminder import ReminderAgent
from backend.agents.safety import SafetyAgent
from backend.config import settings
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
        patient_id: int = 1,
    ) -> None:
        # Single integration point: build the client once and inject it everywhere.
        self._llm = llm or build_llm()
        self._registry = registry or build_default_registry()
        self._history: list[Message] = []
        self._last_route: str = "companion"
        self._patient_id = patient_id
        self._agents = {
            "safety": SafetyAgent(self._llm, self._registry),
            "companion": CompanionAgent(self._llm, self._registry),
            "reminder": ReminderAgent(self._llm, self._registry),
            "behavior": BehaviorAgent(self._llm, self._registry),
            "caregiver": CaregiverLiaisonAgent(self._llm, self._registry),
            "health": HealthAgent(self._llm, self._registry),
        }
        self._load_patient_context(patient_id)
        # Input safety gate, wired ahead of the router. The noise filter is a cheap
        # deterministic scrub; the anomaly gate halts the turn (no specialist, no
        # tool) on outlier / non-related input. Both are toggleable via settings,
        # and the gate shares the router's emergency keywords so it never blocks a
        # possible emergency.
        input_filter = clean_input if settings.input_filter_enabled else None
        self._anomaly = (
            AnomalyDetectionAgent(self._llm, safety_keywords=_SAFETY_KEYWORDS)
            if settings.anomaly_detection_enabled
            else None
        )
        # Compile the LangGraph orchestrator once.
        self._graph = build_guardian_graph(
            self.route, self._agents, input_filter=input_filter, anomaly=self._anomaly
        )

    def set_patient(self, patient_id: int) -> None:
        """Retarget the agent at a different patient.

        Reloads the persona/context block for every specialist and clears the
        running conversation history so a switch doesn't bleed one patient's turns
        into another's. Cheap and idempotent — a no-op if already on this patient.
        """
        if patient_id == self._patient_id:
            return
        self._patient_id = patient_id
        self._history.clear()
        self._last_route = "companion"
        self._load_patient_context(patient_id)

    def clear_history(self) -> None:
        """Forget the running conversation so the next turns start fresh.

        Keeps the current patient + persona context loaded; only the rolling
        message history (and the last-route hint) is wiped, so the LLM answers
        without being anchored to earlier turns.
        """
        self._history.clear()
        self._last_route = "companion"

    def _load_patient_context(self, patient_id: int) -> None:
        from sqlmodel import Session

        from backend.agents.prompts._base import build_patient_context
        from backend.db.session import engine
        from backend.services.patient_profile import PatientNotFoundError, get_patient_profile

        try:
            with Session(engine) as session:
                profile = get_patient_profile(session, patient_id)
            context = build_patient_context(profile)
        except PatientNotFoundError:
            logger.warning(f"Patient #{patient_id} not found; running without patient context.")
            context = ""

        for agent in self._agents.values():
            agent.patient_context = context

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
            max_tokens=24,
            temperature=0.0,
        )
        label = (response.text or "").strip().lower()
        for route in _ROUTES:
            if route in label:
                return route
        return "companion"

    def chat(self, user_message: str) -> str:
        return self.turn(user_message)["reply"]

    def turn(self, user_message: str, emit=None, patient_id: int | None = None) -> dict:
        """One full turn. Returns {route, reply, tool_calls}.

        Tool calls are captured from the per-module audit logs the stubs append to
        (see backend/tools/*). The API layer turns this dict into bus events so the
        Live page shows which specialist ran and which tools fired.

        `emit(kind, payload)` is an optional progress hook streamed step-by-step to
        the live dashboard (routing_decision -> tool_invocation -> agent_reply) as
        the graph runs, instead of all at once after the turn completes.

        `patient_id` retargets the agent before the turn runs, so a single
        long-lived GuardianAgent can serve whichever profile the UI has selected.
        """
        if patient_id is not None:
            self.set_patient(patient_id)
        from backend.tools import emergency, general_tools, health, reminder

        logs = (emergency.CALL_LOG, general_tools.CALL_LOG, health.CALL_LOG, reminder.CALL_LOG)
        for log in logs:
            log.clear()

        # Invoke the compiled graph for this turn. LangGraph traces the run to
        # LangSmith automatically when tracing env vars are set.
        result = self._graph.invoke(
            {"user_message": user_message, "history": list(self._history), "emit": emit},
            config={"run_name": "guardian-turn"},
        )
        reply = result["reply"]
        route = result.get("route", "companion")
        # A blocked turn never ran a specialist; don't let "blocked" become the
        # follow-up hint, and don't anchor history to a rejected utterance.
        if route in _ROUTES:
            self._last_route = route
            self._history.append(Message(role="user", content=user_message))
            self._history.append(Message(role="assistant", content=reply))

        tool_calls = [dict(e) for log in logs for e in log]
        return {"route": route, "reply": reply, "tool_calls": tool_calls}
