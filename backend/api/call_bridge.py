"""Turn a completed agent turn into call_request events for connected phones.

When the agent invokes a call tool, we want a connected Flutter app (on a phone
with a SIM) to place the actual call and play a Kokoro-rendered announcement.
This module inspects the turn result, renders the announcement audio, and
publishes a `CallRequestEvent` onto the bus (which fans out over SSE).

Called from both the HTTP turn endpoint (api/turn.py) and the watch voice
pipeline (api/voice.py), so a call triggered by spoken audio on the watch is
placed by the phone just the same.
"""
from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from backend.events.types import CallRequestEvent
from backend.voice.call_audio import generate_call_wav

CALL_TOOLS = {"call_911", "notify_caregiver", "call_person"}


def _targets(
    tool: str, args: dict[str, Any] | None, result: dict[str, Any] | None
) -> list[tuple[str, str | None, str]]:
    """Return [(phone, contact_name, message)] to dial for one tool invocation."""
    args = args or {}
    result = result or {}

    if tool == "call_911":
        phone = str(result.get("phone") or "911") or "911"
        reason = args.get("reason") or result.get("reason") or "a possible emergency"
        location = args.get("location") or result.get("location") or "the patient's home"
        message = (
            "This is an automated emergency call from Guardian. "
            f"There is {reason}. The person needs help at {location}. "
            "Please send assistance."
        )
        return [(phone, "Emergency services", message)]

    if tool == "call_person":
        phone = str(result.get("phone") or args.get("phone") or "")
        name = result.get("person") or args.get("person")
        message = result.get("message") or args.get("message") or ""
        return [(phone, name, message)] if phone else []

    if tool == "notify_caregiver":
        message = result.get("message") or args.get("message") or ""
        out: list[tuple[str, str | None, str]] = []
        for c in result.get("calls", []) or []:
            phone = str(c.get("phone") or "")
            if phone:
                out.append((phone, c.get("contact"), message))
        return out

    return []


async def emit_call_requests(
    bus: Any, result: dict[str, Any] | None, patient_id: int | None
) -> None:
    """Publish a CallRequestEvent for each call tool the turn invoked."""
    if bus is None or not result:
        return
    route = result.get("route", "safety")
    for tc in result.get("tool_calls", []) or []:
        tool = tc.get("tool") or tc.get("name")
        if tool not in CALL_TOOLS:
            continue
        # In a turn result each tool_call is the tool's return dict (flattened)
        # plus a "tool" key — fields like phone/message/calls live at the top
        # level, and nested args/result may also be present. Pass both views.
        args = tc.get("args") if isinstance(tc.get("args"), dict) else tc
        result = tc.get("result") if isinstance(tc.get("result"), dict) else tc
        for phone, name, message in _targets(tool, args, result):
            audio_url = await asyncio.to_thread(generate_call_wav, message, route)
            try:
                await bus.publish(
                    CallRequestEvent(
                        source=f"tool.{tool}",
                        tool=tool,
                        phone=phone,
                        contact_name=name,
                        message=message,
                        audio_url=audio_url,
                        route=route,
                        patient_id=patient_id,
                    )
                )
                logger.info(f"[call-bridge] call_request {tool} -> {phone} ({audio_url or 'no-audio'})")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[call-bridge] publish failed: {exc}")
