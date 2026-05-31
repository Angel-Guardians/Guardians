"""Emergency tools.

`call_911` remains a stub (real dispatch requires certified integrations).
`notify_caregiver` makes a real outbound phone call via Twilio and reads the
message aloud using OpenAI TTS. Falls back to stub behaviour when Twilio or
OpenAI credentials are not configured, so the agent loop works in dev without
any keys.
"""
from __future__ import annotations

import os
from typing import Any

from backend.llm.base import ToolSpec
from backend.tools.decorators import audit_log, consent_check, idempotent
from dotenv import load_dotenv

load_dotenv()

CALL_LOG: list[dict[str, Any]] = []


def _normalize_contacts(
    contacts: list[str] | str | None, contact: str | None
) -> list[str]:
    """Coerce the model's contact selection into a clean list of names/relationships.

    Tolerates a single string, a list, or the legacy ``contact=`` singular arg.
    An empty result means "no one named" → caller defaults to priority-1.
    """
    out: list[str] = []
    if isinstance(contacts, str):
        out.append(contacts)
    elif isinstance(contacts, list):
        out.extend(str(c) for c in contacts)
    if contact:
        out.append(contact)
    return [c.strip() for c in out if c and c.strip()]


@audit_log
@idempotent(window_seconds=60)
def call_911(reason: str, location: str = "patient home") -> dict[str, Any]:
    """Call emergency services via Twilio <Say>.

    In production, TWILIO_911_NUMBER should be a certified dispatch line.
    For dev/testing, set it to any phone number you want to receive the call.
    Falls back to stub when Twilio credentials or the emergency number are absent.
    """
    twilio_ready = bool(
        os.getenv("TWILIO_ACCOUNT_SID")
        and os.getenv("TWILIO_AUTH_TOKEN")
        and os.getenv("TWILIO_FROM_NUMBER")
    )
    emergency_number = os.getenv("TWILIO_911_NUMBER", "")

    if not twilio_ready or not emergency_number:
        event = {
            "tool": "call_911",
            "status": "stub",
            "service": "EMS",
            "eta_minutes": 8,
            "reason": reason,
            "location": location,
            "note": "Set TWILIO_* and TWILIO_911_NUMBER in .env to enable real calls.",
        }
        CALL_LOG.append(event)
        return event

    spoken_message = (
        f"Emergency alert. A Guardian AI system is reporting an incident. "
        f"Reason: {reason}. Location: {location}. "
        f"Please send emergency medical services immediately."
    )

    from twilio.rest import Client as TwilioClient

    twilio = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    twiml = f'<Response><Say voice="Polly.Joanna">{spoken_message}</Say></Response>'
    call = twilio.calls.create(
        to=emergency_number,
        from_=os.getenv("TWILIO_FROM_NUMBER"),
        twiml=twiml,
    )

    event = {
        "tool": "call_911",
        "status": "called",
        "service": "EMS",
        "phone": emergency_number,
        "reason": reason,
        "location": location,
        "call_sid": call.sid,
    }
    CALL_LOG.append(event)
    return event


@audit_log
@consent_check(recipient="family", data_category="status_update")
@idempotent(window_seconds=60)
def notify_caregiver(
    message: str,
    contacts: list[str] | str | None = None,
    contact: str | None = None,
) -> dict[str, Any]:
    """Call one or more of the patient's emergency contacts and read a message aloud.

    The model chooses *who* to reach by name or relationship (e.g. ["Maria"],
    ["daughter", "family_doctor"]); the phone numbers are retrieved from the
    patient's emergency-contact list in the DB — never passed in by the model.
    When no contact is named, the highest-priority contact is used.

    Falls back to a stub (showing who *would* be called) when Twilio credentials
    are absent, so the agent loop works in dev/test without any external keys.
    """
    requested = _normalize_contacts(contacts, contact)

    from sqlmodel import Session

    from backend.db.session import engine
    from backend.tools._contacts import default_patient_id, resolve_contacts

    with Session(engine) as session:
        patient_id = default_patient_id(session)
        targets = resolve_contacts(session, patient_id, requested) if patient_id else []
        # Detach the fields we need before the session closes.
        resolved = [(c.name, c.relationship, c.phone) for c in targets]

    if not resolved:
        event = {
            "tool": "notify_caregiver",
            "status": "error",
            "requested": requested,
            "message": message,
            "error": "No matching emergency contact on file for the patient.",
        }
        CALL_LOG.append(event)
        return event

    twilio_ready = bool(
        os.getenv("TWILIO_ACCOUNT_SID")
        and os.getenv("TWILIO_AUTH_TOKEN")
        and os.getenv("TWILIO_FROM_NUMBER")
    )

    if not twilio_ready:
        event = {
            "tool": "notify_caregiver",
            "status": "stub",
            "channel": "none",
            "message": message,
            "calls": [
                {"contact": name, "relationship": rel, "phone": phone, "status": "stub"}
                for name, rel, phone in resolved
            ],
            "note": "Set TWILIO_* in .env to enable real calls.",
        }
        CALL_LOG.append(event)
        return event

    from twilio.rest import Client as TwilioClient

    twilio = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    twiml = f'<Response><Say voice="Polly.Joanna">{message}</Say></Response>'
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    calls: list[dict[str, Any]] = []
    for name, rel, phone in resolved:
        if not phone:
            calls.append(
                {"contact": name, "relationship": rel, "status": "error",
                 "error": "no phone number on file"}
            )
            continue
        call = twilio.calls.create(to=phone, from_=from_number, twiml=twiml)
        calls.append(
            {"contact": name, "relationship": rel, "phone": phone,
             "status": "called", "call_sid": call.sid}
        )

    event = {
        "tool": "notify_caregiver",
        "status": "called",
        "channel": "voice",
        "message": message,
        "calls": calls,
    }
    CALL_LOG.append(event)
    return event


def register(registry) -> None:
    registry.register(
        ToolSpec(
            name="call_911",
            description="Call emergency services (911). Use only for a genuine "
            "emergency: fall, chest pain, difficulty breathing, unresponsiveness. "
            "This places a real phone call — only invoke when the situation is critical.",
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
            description=(
                "Call one or more of the patient's emergency contacts and read them a "
                "voice message. Choose who to reach from the emergency contacts listed "
                "in your patient context, by name or relationship — the phone numbers "
                "are looked up automatically, so never pass a number. Omit 'contacts' "
                "to reach the highest-priority contact. Use for urgent situations where "
                "a caregiver must be informed immediately."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to read aloud to the contact(s).",
                    },
                    "contacts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Names or relationships of the emergency contacts to call "
                            "(e.g. ['Maria'] or ['daughter', 'family_doctor']). "
                            "Omit to use the highest-priority contact."
                        ),
                    },
                },
                "required": ["message"],
            },
        ),
        notify_caregiver,
    )
