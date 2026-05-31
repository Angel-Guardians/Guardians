"""Live event stream over SSE for the UI.

Subscribes to the in-process EventBus and serialises every GuardianEvent into the
shape the frontend expects: {id, kind, ts, summary, payload}. The Live page keys
its transcript pane off kind == "transcript"; everything else lands in the log.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from backend.events.types import GuardianEvent

router = APIRouter()


def _summarise(ev: GuardianEvent) -> str:
    """Human-readable one-liner per event type for the Live log."""
    d = ev.model_dump(mode="json")
    t = d.get("type", ev.__class__.__name__)
    if t == "transcript":
        return d.get("text", "")
    if t == "agent_reply":
        return f'{d.get("agent", "guardian")}: {d.get("text", "")}'
    if t == "routing_decision":
        return f'routed to {d.get("routed_to")} ({d.get("rationale") or "—"})'
    if t == "tool_invocation":
        return f'{d.get("tool")}() -> {json.dumps(d.get("result_summary") or {})[:120]}'
    if t == "call_request":
        who = d.get("contact_name") or d.get("phone")
        return f'call {who} ({d.get("phone")})'
    if t == "vital_sample":
        return f'{d.get("kind")} = {d.get("value")} ({d.get("device")})'
    if t == "risk_score_updated":
        return f'risk {d.get("level")} ({d.get("score")})'
    return t


def serialise(ev: GuardianEvent) -> dict[str, str]:
    d = ev.model_dump(mode="json")
    kind = d.get("type", ev.__class__.__name__)
    return {
        "data": json.dumps(
            {
                "id": str(d.get("id")),
                "kind": kind,
                "ts": d.get("ts"),
                "summary": _summarise(ev),
                "payload": d,
            }
        )
    }


@router.get("/sse")
async def event_stream(request: Request) -> EventSourceResponse:
    bus = request.app.state.event_bus

    async def _gen() -> AsyncIterator[dict[str, str]]:
        async for ev in bus.stream():
            if await request.is_disconnected():
                break
            yield serialise(ev)

    return EventSourceResponse(_gen())
