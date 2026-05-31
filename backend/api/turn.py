"""Conversational turn endpoint.

POST /turn { "text": "...", "patient_id": 1 }

Runs one turn through the LangGraph GuardianAgent (built once at startup and held
on app.state.guardian). Progress is streamed onto the EventBus **step-by-step as it
happens** — patient utterance, the routing decision, each tool invocation, and the
spoken reply — so the Live page shows exactly which step the agent is on, rather
than jumping straight to the final state.

The graph is synchronous, so it runs in a worker thread (`asyncio.to_thread`). The
`emit` callback it receives is thread-safe: it schedules `bus.publish(...)` back
onto the main event loop via `run_coroutine_threadsafe`, so each step surfaces the
instant it occurs. The agent itself is provider-neutral: same code path on OpenAI
cloud or a local DGX Spark endpoint — only .env changes.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.api.call_bridge import emit_call_requests
from backend.events.types import (
    AgentReplyEvent,
    PipelineStepEvent,
    RoutingDecisionEvent,
    ToolInvocationEvent,
    TranscriptEvent,
)
from backend.voice.dashboard import speak_reply

router = APIRouter()


class TurnRequest(BaseModel):
    text: str
    patient_id: int = 1
    # When true, the reply is also rendered with Kokoro and streamed to any
    # dashboard listening on /voice/listen (the Live page speaker). The web UI
    # leaves this off; the scripted demo turns it on so Guardian is heard aloud.
    speak: bool = False


class TurnResponse(BaseModel):
    route: str
    reply: str
    tool_calls: list[dict]


def _event_for(kind: str, payload: dict):
    """Map an agent-layer (kind, payload) step to a typed GuardianEvent.

    `kind` matches the frontend pipeline vocabulary exactly, so the Live graph
    animates with no translation. Returns None for unknown kinds.
    """
    if kind == "input_filtered":
        removed = payload.get("removed") or []
        return PipelineStepEvent(
            source="agent.filter",
            node_id="filter",
            status="done",
            detail="scrubbed " + ", ".join(removed) if removed else "no noise found",
        )
    if kind == "input_rejected":
        return PipelineStepEvent(
            source="agent.anomaly",
            node_id="anomaly",
            status="error",
            detail=payload.get("reason") or "input rejected",
        )
    if kind == "routing_decision":
        return RoutingDecisionEvent(
            source="agent.router",
            routed_to=payload["routed_to"],
            rationale=payload.get("rationale"),
        )
    if kind == "tool_invocation":
        tool = payload.get("tool", "unknown")
        return ToolInvocationEvent(
            source=f"tool.{tool}",
            tool=tool,
            args_summary=payload.get("args") or {},
            result_summary=payload.get("result"),
        )
    if kind == "agent_reply":
        agent = payload.get("agent", "companion")
        return AgentReplyEvent(source=f"agent.{agent}", agent=agent, text=payload.get("text", ""))
    return None


@router.post("/", response_model=TurnResponse)
async def take_turn(body: TurnRequest, request: Request) -> TurnResponse:
    guardian = request.app.state.guardian
    bus = request.app.state.event_bus
    loop = asyncio.get_running_loop()

    def emit(kind: str, payload: dict) -> None:
        """Called from the agent's worker thread; hop back onto the loop to publish."""
        if bus is None:
            return
        event = _event_for(kind, payload)
        if event is not None:
            asyncio.run_coroutine_threadsafe(bus.publish(event), loop)

    # Transcript first so the Live graph resets to a fresh turn before steps stream.
    if bus is not None:
        await bus.publish(TranscriptEvent(source="api.turn", text=body.text))

    # Run the synchronous graph off the loop; steps stream live via `emit`.
    # body.patient_id retargets the agent so the reply is grounded in the
    # profile the UI currently has selected.
    result = await asyncio.to_thread(guardian.turn, body.text, emit, body.patient_id)

    # If the agent decided to place a call, push a call_request (with Kokoro
    # audio) to any connected phone so it dials + speaks the announcement.
    await emit_call_requests(bus, result, body.patient_id)

    # Demo path: voice the reply through Kokoro to the Live page speaker. Fire it
    # off so the HTTP response returns immediately while audio streams.
    if body.speak:
        monitor = getattr(request.app.state, "voice_monitor", None)
        asyncio.create_task(
            speak_reply(monitor, result.get("reply", ""), result.get("route", "companion"))
        )

    return TurnResponse(**result)


@router.post("/clear")
async def clear_context(request: Request) -> dict:
    """Wipe the agent's running conversation history so answers start fresh.

    The patient profile/persona stays loaded — only the prior turns are dropped.
    """
    guardian = request.app.state.guardian
    if guardian is not None:
        guardian.clear_history()
    bus = getattr(request.app.state, "event_bus", None)
    if bus is not None:
        await bus.publish(TranscriptEvent(source="api.turn", text="— context cleared —"))
    return {"cleared": True}
