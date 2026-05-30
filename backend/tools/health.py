"""Health tool stubs (Phase-1 placeholders)."""
from __future__ import annotations

from typing import Any

from backend.llm.base import ToolSpec

CALL_LOG: list[dict[str, Any]] = []


def log_vital(metric: str, value: str, unit: str = "") -> dict[str, Any]:
    """STUB: pretend to persist a vital sign reading."""
    event = {"tool": "log_vital", "status": "recorded", "metric": metric, "value": value, "unit": unit}
    CALL_LOG.append(event)
    return event


def get_medications() -> dict[str, Any]:
    """STUB: return the patient's medication list."""
    return {
        "tool": "get_medications",
        "medications": [
            {"name": "metoprolol", "dose": "50 mg", "schedule": "morning"},
            {"name": "aspirin", "dose": "81 mg", "schedule": "morning"},
        ],
    }


def register(registry) -> None:
    registry.register(
        ToolSpec(
            name="log_vital",
            description="Record a vital sign the patient reports (e.g. heart rate, blood pressure).",
            parameters={
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "description": "e.g. heart_rate, blood_pressure."},
                    "value": {"type": "string"},
                    "unit": {"type": "string"},
                },
                "required": ["metric", "value"],
            },
        ),
        log_vital,
    )
    registry.register(
        ToolSpec(
            name="get_medications",
            description="Look up the patient's current medication list.",
            parameters={"type": "object", "properties": {}},
        ),
        get_medications,
    )
