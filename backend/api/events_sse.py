"""Live event stream over SSE for the UI."""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


@router.get("/sse")
async def event_stream(request: Request) -> EventSourceResponse:
    """Stream events to the UI."""

    async def _gen() -> AsyncIterator[dict[str, str]]:
        # TODO: get bus from app.state, subscribe, yield serialized events
        if False:
            yield {"event": "noop", "data": "{}"}
        raise NotImplementedError

    return EventSourceResponse(_gen())
