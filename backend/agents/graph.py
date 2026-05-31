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


def build_guardian_graph(
    route_fn: Callable[[str], str],
    agents: dict[str, ToolCallingAgent],
):
    """Compile the router + specialist graph.

    `route_fn` is the hybrid keyword/LLM classifier; `agents` maps a route name to
    its specialist. Returns a compiled graph exposing `.invoke(state)`.
    """

    def router_node(state: GuardianState) -> GuardianState:
        return {"route": route_fn(state["user_message"], state.get("history", []))}

    def make_specialist_node(agent: ToolCallingAgent) -> Callable[[GuardianState], GuardianState]:
        def node(state: GuardianState) -> GuardianState:
            reply = agent.chat(state["user_message"], state.get("history", []))
            return {"reply": reply}

        return node

    graph = StateGraph(GuardianState)
    graph.add_node("router", router_node)
    for name, agent in agents.items():
        graph.add_node(name, make_specialist_node(agent))

    graph.add_edge(START, "router")
    # Conditional fan-out: the router's chosen route name selects the next node.
    graph.add_conditional_edges("router", lambda s: s["route"], {name: name for name in agents})
    for name in agents:
        graph.add_edge(name, END)

    return graph.compile()
