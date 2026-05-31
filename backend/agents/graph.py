"""LangGraph orchestration for Guardian.

The orchestrator is a `StateGraph`:

        START -> router -> (conditional) -> {safety | companion | reminder |
                                             behavior | caregiver | health} -> END

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

from backend.agents.base import ToolCallingAgent
from backend.llm.base import Message


class GuardianState(TypedDict, total=False):
    """State threaded through one turn of the graph."""

    user_message: str
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
):
    """Compile the router + specialist graph.

    `route_fn` is the hybrid keyword/LLM classifier; `agents` maps a route name to
    its specialist. Returns a compiled graph exposing `.invoke(state)`.
    """

    def router_node(state: GuardianState) -> GuardianState:
        route = route_fn(state["user_message"], state.get("history", []))
        emit = state.get("emit")
        if emit is not None:
            emit("routing_decision", {"routed_to": route, "rationale": "keyword/LLM hybrid"})
        return {"route": route}

    def make_specialist_node(
        name: str, agent: ToolCallingAgent
    ) -> Callable[[GuardianState], GuardianState]:
        def node(state: GuardianState) -> GuardianState:
            emit = state.get("emit")
            reply = agent.chat(state["user_message"], state.get("history", []), emit=emit)
            if emit is not None:
                emit("agent_reply", {"agent": name, "text": reply})
            return {"reply": reply}

        return node

    graph = StateGraph(GuardianState)
    graph.add_node("router", router_node)
    for name, agent in agents.items():
        graph.add_node(name, make_specialist_node(name, agent))

    graph.add_edge(START, "router")
    # Conditional fan-out: the router's chosen route name selects the next node.
    graph.add_conditional_edges("router", lambda s: s["route"], {name: name for name in agents})
    for name in agents:
        graph.add_edge(name, END)

    return graph.compile()
