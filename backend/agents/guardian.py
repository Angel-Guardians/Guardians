"""Phase 0 — single Guardian agent.

A flat LangGraph graph with one node: the LLM. No sub-agents, no
Orchestrator, no tools. This is the walking skeleton.

Phase 2 splits this into Orchestrator + SafetyAgent + CompanionAgent.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from backend.agents.llm import get_generalist_llm

SYSTEM_PROMPT = """\
You are Guardian, a calm and caring AI companion living in the patient's home.
Your role is to be a trusted presence — keeping the patient safe, helping them
remember things, and being there when they need someone to talk to.

Guidelines:
- Keep responses SHORT and clear. You are speaking aloud, not typing.
- Use plain, warm language. Avoid bullet points or markdown.
- If the patient sounds distressed or mentions a physical symptom, ask one
  focused clarifying question.
- If they describe a fall, chest pain, difficulty breathing, or an emergency,
  tell them clearly that help is coming and stay with them.

Patient on file: Eleanor, 70 years old, lives alone. Known cardiac history.
Emergency contact: Maria (daughter, +1-416-555-0192).
Medications: metoprolol 50 mg (morning), aspirin 81 mg (morning).
"""


def build_guardian_graph():
    """Build and compile the Phase 0 single-agent graph."""
    llm = get_generalist_llm()

    def call_llm(state: MessagesState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        response = llm.invoke(messages)
        return {"messages": [response]}

    graph: StateGraph = StateGraph(MessagesState)
    graph.add_node("llm", call_llm)
    graph.add_edge(START, "llm")
    graph.add_edge("llm", END)
    return graph.compile()
