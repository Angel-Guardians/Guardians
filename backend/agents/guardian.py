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
from loguru import logger

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
living alone. Read the person's latest message and reply with exactly ONE
category word. Catching emergencies is the most important job — when unsure
between safety and anything else, choose safety.

  safety    — emergencies or physical danger: a fall, chest pain, trouble
              breathing, severe pain, bleeding, fainting, a racing or irregular
              heartbeat, "I'm dying", or feeling something is very wrong.
  reminder  — medication timing, appointments, or the daily schedule.
  caregiver — an explicit request to contact or message family or a caregiver.
  health    — a specific non-emergency symptom or vital reading.
  behavior  — noticing mood shifts, withdrawal, confusion, or sleep/appetite changes.
  companion — the default home base: ordinary conversation, company, emotional
              support, loneliness, mood, and short replies ("yes", "done").

Rules:
- Reply with exactly ONE word from the list. No punctuation, no explanation.
- companion is home base: if the message is just conversation, feelings, or a
  short reply, choose companion.
- Emergencies ALWAYS win: any sign of physical danger goes to safety, not companion.

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

Reply with exactly one word.
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
        # Compile the LangGraph orchestrator once.
        self._graph = build_guardian_graph(self.route, self._agents)

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

    def _load_patient_context(self, patient_id: int) -> None:
        from backend.agents.prompts._base import build_patient_context
        from backend.db.session import engine
        from backend.services.patient_profile import PatientNotFoundError, get_patient_profile
        from sqlmodel import Session

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

        # Classify on the current message alone. Feeding prior turns + a
        # "stick to the last agent" hint created a companion gravity well:
        # once a turn landed on companion (the default), follow-ups stayed there
        # and real intents got swallowed. companion is still the fallback below,
        # so ordinary short replies route there naturally without the bias.
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
                logger.info(f"[router] {message!r} -> {route} (model said {label!r})")
                return route
        # No category matched the model's reply — fall back to companion. Logged
        # at WARNING so an unexpected default is visible while debugging routing.
        logger.warning(
            f"[router] no category matched model reply {label!r} for {message!r}; "
            "defaulting to companion"
        )
        return "companion"

    def reset(self) -> None:
        """Wipe the conversation memory so a test or demo run starts clean.

        Clears the in-process history shared across all specialists and the
        last-route marker. The next turn behaves as if the backend just booted,
        with no prior context — used by POST /turn/reset (e.g. on page refresh).
        """
        self._history.clear()
        self._last_route = "companion"

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
        self._last_route = route
        self._history.append(Message(role="user", content=user_message))
        self._history.append(Message(role="assistant", content=reply))

        tool_calls = [dict(e) for log in logs for e in log]
        return {"route": route, "reply": reply, "tool_calls": tool_calls}
