"""Reminder tool stubs (Phase-1 placeholders)."""
from __future__ import annotations

from typing import Any

from backend.llm.base import ToolSpec

CALL_LOG: list[dict[str, Any]] = []


def get_schedule() -> dict[str, Any]:
    """STUB: return today's schedule."""
    return {
        "tool": "get_schedule",
        "items": [
            {"time": "08:00", "what": "metoprolol 50 mg + aspirin 81 mg"},
            {"time": "12:30", "what": "lunch"},
            {"time": "15:00", "what": "call with Maria"},
        ],
    }


def mark_med_taken(medication: str) -> dict[str, Any]:
    """STUB: record that a medication was taken."""
    event = {"tool": "mark_med_taken", "status": "acknowledged", "medication": medication}
    CALL_LOG.append(event)
    return event


def register(registry) -> None:
    registry.register(
        ToolSpec(
            name="get_schedule",
            description="Look up the patient's schedule and medication times for today.",
            parameters={"type": "object", "properties": {}},
        ),
        get_schedule,
    )
    registry.register(
        ToolSpec(
            name="mark_med_taken",
            description="Record that the patient has taken a medication.",
            parameters={
                "type": "object",
                "properties": {"medication": {"type": "string"}},
                "required": ["medication"],
            },
        ),
        mark_med_taken,
    )
