"""General communication tools.

`call_person` places an outbound phone call to a named person and reads a message
aloud via Twilio <Say>. The model picks the person by name or relationship from the
patient's emergency contacts; the phone number is retrieved from the DB. An explicit
E.164 number may be passed to reach someone not on the contact list. Falls back to
stub behaviour when Twilio credentials are not configured, so the agent loop works in
dev without any keys.
"""
from __future__ import annotations

import os
from typing import Any

from backend.llm.base import ToolSpec
from backend.tools.decorators import audit_log, consent_check, idempotent
from dotenv import load_dotenv

load_dotenv()

CALL_LOG: list[dict[str, Any]] = []


def _lookup_contact(person: str) -> tuple[str, str] | None:
    """Resolve a name/relationship to (matched_name, phone) from the DB, or None."""
    from sqlmodel import Session

    from backend.db.session import engine
    from backend.tools._contacts import default_patient_id, resolve_contacts

    with Session(engine) as session:
        patient_id = default_patient_id(session)
        if patient_id is None:
            return None
        matches = resolve_contacts(session, patient_id, [person])
        if not matches:
            return None
        top = matches[0]
        return (top.name, top.phone)


@audit_log
@consent_check(recipient="contact", data_category="status_update")
@idempotent(window_seconds=60)
def call_person(
    person: str,
    message: str,
    phone: str = "",
) -> dict[str, Any]:
    """Call a person by name and read them a message aloud via Twilio <Say>.

    Resolves the number from the patient's emergency contacts (by name or
    relationship). An explicit ``phone`` overrides the lookup. Falls back to a
    stub when Twilio credentials are absent.
    """
    # Resolve who we're calling: an explicit number wins, else the contact list.
    to_number = phone
    matched_name = person
    if not to_number:
        found = _lookup_contact(person)
        if found is not None:
            matched_name, to_number = found

    if not to_number:
        event = {
            "tool": "call_person",
            "status": "error",
            "person": person,
            "message": message,
            "error": (
                f"No phone number found for '{person}'. They are not in the patient's "
                "emergency contacts; pass an explicit phone number to reach them."
            ),
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
            "tool": "call_person",
            "status": "stub",
            "person": matched_name,
            "phone": to_number,
            "message": message,
            "note": "Set TWILIO_* in .env to enable real calls.",
        }
        CALL_LOG.append(event)
        return event

    from twilio.rest import Client as TwilioClient

    twilio = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    twiml = f'<Response><Say voice="Polly.Joanna">{message}</Say></Response>'
    call = twilio.calls.create(
        to=to_number,
        from_=os.getenv("TWILIO_FROM_NUMBER"),
        twiml=twiml,
    )

    event = {
        "tool": "call_person",
        "status": "called",
        "channel": "voice",
        "person": matched_name,
        "phone": to_number,
        "message": message,
        "call_sid": call.sid,
    }
    CALL_LOG.append(event)
    return event


def register(registry) -> None:
    registry.register(
        ToolSpec(
            name="call_person",
            description=(
                "Place an outbound phone call to a named person and read them a voice message. "
                "Use for non-emergency situations where you need to reach someone — for example, "
                "reminders, check-ins, or passing along information. "
                "For genuine emergencies use call_911 or notify_caregiver instead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "person": {
                        "type": "string",
                        "description": "Name of the person to call (e.g. 'Dr. Smith', 'Sophie').",
                    },
                    "message": {
                        "type": "string",
                        "description": "The message to read aloud to the person.",
                    },
                    "phone": {
                        "type": "string",
                        "description": (
                            "Phone number in E.164 format (e.g. '+15555550111'). "
                            "Leave blank to look up the number by name from the contact book."
                        ),
                    },
                },
                "required": ["person", "message"],
            },
        ),
        call_person,
    )
