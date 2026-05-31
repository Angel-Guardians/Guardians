"""LangGraph orchestration for Guardian.

The orchestrator is a `StateGraph`:

        START -> preprocess -> anomaly -> (conditional) ->
                    blocked -> END                              (input rejected)
                    router -> (conditional) -> {safety | companion | reminder |
                                                behavior | caregiver | health} -> END

`preprocess` runs the deterministic noise/sound filter (backend.agents.input_filter)
so every downstream node sees scrubbed text. `anomaly` is the gate
(backend.agents.anomaly): if it flags the input as an outlier / non-related, the
turn short-circuits to `blocked` and NO specialist or tool runs.

Each node runs against the provider-neutral `LLMClient`, so the graph is identical
on OpenAI cloud or a local DGX Spark endpoint. When LangSmith tracing is enabled
(LANGSMITH_TRACING=true + LANGSMITH_API_KEY), LangGraph automatically emits a span
per node and nests the model calls underneath — full end-to-end observability of
which specialist ran and which tools fired, with no extra code.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agents.anomaly import AnomalyDetectionAgent
from backend.agents.base import ToolCallingAgent
from backend.agents.input_filter import FilteredInput
from backend.llm.base import Message


class GuardianState(TypedDict, total=False):
    """State threaded through one turn of the graph."""

    user_message: str  # raw input as received
    clean_message: str  # noise-filtered text; what every node downstream reads
    input_is_noise: bool  # the filter found nothing intelligible
    blocked: bool  # the anomaly gate rejected the input
    block_reason: str
    block_kind: str  # "noise" | "offtopic" — selects the clarifying reply
    history: list[Message]
    route: str
    reply: str
    # Optional per-turn progress hook: emit(kind, payload). Carries the live
    # dashboard's step events (routing_decision / tool_invocation / agent_reply)
    # as they happen. Absent on headless runs, so the graph still works offline.
    emit: object


def build_guardian_graph(
    route_fn: Callable[[str], str],
    agents: dict[str, ToolCallingAgent],
    input_filter: Callable[[str], FilteredInput] | None = None,
    anomaly: AnomalyDetectionAgent | None = None,
):
    """Compile the preprocess + gate + router + specialist graph.

    `route_fn` is the hybrid keyword/LLM classifier; `agents` maps a route name to
    its specialist. `input_filter` scrubs noise before any model sees the text;
    `anomaly` gates outlier / non-related inputs. Both are optional — when omitted
    the graph behaves exactly as before (raw text straight to the router). Returns
    a compiled graph exposing `.invoke(state)`.
    """

    def _text(state: GuardianState) -> str:
        """The text downstream nodes act on: filtered when available, else raw."""
        return state.get("clean_message") or state["user_message"]

    def preprocess_node(state: GuardianState) -> GuardianState:
        if input_filter is None:
            return {"clean_message": state["user_message"], "input_is_noise": False}
        result = input_filter(state["user_message"])
        emit = state.get("emit")
        if emit is not None and result.removed:
            emit("input_filtered", {"removed": result.removed, "clean": result.text})
        return {"clean_message": result.text, "input_is_noise": result.is_noise}

    def anomaly_node(state: GuardianState) -> GuardianState:
        if anomaly is None:
            return {"blocked": False}
        verdict = anomaly.check(_text(state), is_noise=state.get("input_is_noise", False))
        if verdict.ok:
            return {"blocked": False}
        emit = state.get("emit")
        if emit is not None:
            emit("input_rejected", {"reason": verdict.reason, "kind": verdict.kind})
        return {"blocked": True, "block_reason": verdict.reason, "block_kind": verdict.kind}

    def blocked_node(state: GuardianState) -> GuardianState:
        # Terminal: input was rejected, so no specialist and no tool runs. Return a
        # short clarification as the spoken reply instead.
        from backend.agents.anomaly import AnomalyVerdict

        verdict = AnomalyVerdict(ok=False, kind=state.get("block_kind", ""))
        reply = (
            anomaly.refusal_reply(verdict)
            if anomaly is not None
            else "I'm sorry, I didn't quite catch that. Could you say that again?"
        )
        emit = state.get("emit")
        if emit is not None:
            emit("agent_reply", {"agent": "guardian", "text": reply})
        return {"reply": reply, "route": "blocked"}

    def router_node(state: GuardianState) -> GuardianState:
        route = route_fn(_text(state), state.get("history", []))
        emit = state.get("emit")
        if emit is not None:
            emit("routing_decision", {"routed_to": route, "rationale": "keyword/LLM hybrid"})
        return {"route": route}

    def make_specialist_node(
        name: str, agent: ToolCallingAgent
    ) -> Callable[[GuardianState], GuardianState]:
        def node(state: GuardianState) -> GuardianState:
            emit = state.get("emit")
            reply = agent.chat(_text(state), state.get("history", []), emit=emit)
            if emit is not None:
                emit("agent_reply", {"agent": name, "text": reply})
            return {"reply": reply}

        return node

    graph = StateGraph(GuardianState)
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("anomaly", anomaly_node)
    graph.add_node("blocked", blocked_node)
    graph.add_node("router", router_node)
    for name, agent in agents.items():
        graph.add_node(name, make_specialist_node(name, agent))

    graph.add_edge(START, "preprocess")
    graph.add_edge("preprocess", "anomaly")
    # Gate: a rejected input goes to `blocked` and stops; otherwise on to routing.
    graph.add_conditional_edges(
        "anomaly",
        lambda s: "blocked" if s.get("blocked") else "router",
        {"blocked": "blocked", "router": "router"},
    )
    graph.add_edge("blocked", END)
    # Conditional fan-out: the router's chosen route name selects the next node.
    graph.add_conditional_edges("router", lambda s: s["route"], {name: name for name in agents})
    for name in agents:
        graph.add_edge(name, END)

    return graph.compile()
