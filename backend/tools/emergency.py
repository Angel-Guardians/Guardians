"""Emergency tool stubs.

Phase-1 placeholders. Each accepts arguments and returns a deterministic canned
response so the agent->tool->agent loop can be validated end-to-end without any
real dispatch or messaging integration.
"""
from __future__ import annotations

from typing import Any

from backend.llm.base import ToolSpec

# A module-level audit trail makes the stubs observable from tests/demos.
CALL_LOG: list[dict[str, Any]] = []


def call_911(reason: str, location: str = "patient home") -> dict[str, Any]:
    """STUB: pretend to dispatch emergency medical services."""
    event = {
        "tool": "call_911",
        "status": "dispatched",
        "service": "EMS",
        "eta_minutes": 8,
        "reason": reason,
        "location": location,
    }
    CALL_LOG.append(event)
    return event


def notify_caregiver(message: str, contact: str = "Maria") -> dict[str, Any]:
    """STUB: pretend to text/call the emergency contact."""
    event = {
        "tool": "notify_caregiver",
        "status": "sent",
        "channel": "sms",
        "contact": contact,
        "message": message,
    }
    CALL_LOG.append(event)
    return event


def register(registry) -> None:
    registry.register(
        ToolSpec(
            name="call_911",
            description="Dispatch emergency medical services. Use only for a genuine "
            "emergency: fall, chest pain, difficulty breathing, unresponsiveness.",
            parameters={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Brief reason for the call."},
                    "location": {"type": "string", "description": "Where the patient is."},
                },
                "required": ["reason"],
            },
        ),
        call_911,
    )
    registry.register(
        ToolSpec(
            name="notify_caregiver",
            description="Send a message to the patient's emergency contact / family caregiver.",
            parameters={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "What to tell the caregiver."},
                    "contact": {"type": "string", "description": "Caregiver name."},
                },
                "required": ["message"],
            },
        ),
        notify_caregiver,
    )
