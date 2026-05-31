"""Conversational turn endpoint.

POST /turn { "text": "...", "patient_id": 1 }

Runs one turn through the LangGraph GuardianAgent (built once at startup and held
on app.state.guardian), then publishes the patient utterance, the routing decision,
each tool invocation, and Guardian's spoken reply onto the EventBus so the Live page
streams them in real time. The agent itself is provider-neutral: same code path on
OpenAI cloud or a local DGX Spark endpoint — only .env changes.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.events.types import (
    AgentReplyEvent,
    RoutingDecisionEvent,
    ToolInvocationEvent,
    TranscriptEvent,
)

router = APIRouter()


class TurnRequest(BaseModel):
    text: str
    patient_id: int = 1


class TurnResponse(BaseModel):
    route: str
    reply: str
    tool_calls: list[dict]


@router.post("/", response_model=TurnResponse)
async def take_turn(body: TurnRequest, request: Request) -> TurnResponse:
    guardian = request.app.state.guardian
    bus = request.app.state.event_bus

    # The graph is synchronous; keep the event loop free.
    result = await asyncio.to_thread(guardian.turn, body.text)

    await bus.publish(TranscriptEvent(source="api.turn", text=body.text))
    await bus.publish(
        RoutingDecisionEvent(
            source="agent.router",
            routed_to=result["route"],
            rationale="keyword fast-path or LLM triage",
        )
    )
    for call in result["tool_calls"]:
        await bus.publish(
            ToolInvocationEvent(
                source=f"tool.{call.get('tool', 'unknown')}",
                tool=call.get("tool", "unknown"),
                args_summary={k: v for k, v in call.items() if k != "tool"},
                result_summary=call,
            )
        )
    await bus.publish(
        AgentReplyEvent(source=f"agent.{result['route']}", agent=result["route"], text=result["reply"])
    )

    return TurnResponse(**result)


@router.post("/reset")
async def reset_context(request: Request) -> dict:
    """Clear Guardian's conversation memory so a test run starts fresh.

    No-op-safe if the agent failed to initialise. The Live page calls this when
    the user clicks "Reset context".
    """
    guardian = request.app.state.guardian
    if guardian is not None:
        guardian.reset()
    return {"ok": True}
