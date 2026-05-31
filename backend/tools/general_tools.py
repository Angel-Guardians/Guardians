"""General communication tools.

`call_person` places an outbound phone call to a named contact and reads
a message aloud via Twilio <Say>.  Falls back to stub behaviour when Twilio
credentials are not configured, so the agent loop works in dev without any keys.
"""
from __future__ import annotations

import os
from typing import Any

from backend.llm.base import ToolSpec
from dotenv import load_dotenv

load_dotenv()

CALL_LOG: list[dict[str, Any]] = []


def _build_contact_book() -> dict[str, str]:
    book: dict[str, str] = {}
    for entry in os.getenv("CONTACT_BOOK", "").split(";"):
        entry = entry.strip()
        if ":" in entry:
            name, phone = entry.split(":", 1)
            book[name.strip().lower()] = phone.strip()
    return book


def _resolve_phone(person: str, phone: str) -> str:
    """Return `phone` if provided, otherwise look up `person` in the contact book."""
    if phone:
        return phone
    return _build_contact_book().get(person.lower(), "")


def call_person(
    person: str,
    message: str,
    phone: str = "",
) -> dict[str, Any]:
    """Call a person by name and read them a message aloud via Twilio <Say>.

    Falls back to a stub response when Twilio credentials are absent.
    """
    twilio_ready = bool(
        os.getenv("TWILIO_ACCOUNT_SID")
        and os.getenv("TWILIO_AUTH_TOKEN")
        and os.getenv("TWILIO_FROM_NUMBER")
    )

    if not twilio_ready:
        event = {
            "tool": "call_person",
            "status": "stub",
            "person": person,
            "message": message,
            "note": "Set TWILIO_* in .env to enable real calls.",
        }
        CALL_LOG.append(event)
        return event

    to_number = _resolve_phone(person, phone) or os.getenv("TWILIO_TEST_TO_NUMBER", "")
    if not to_number:
        event = {
            "tool": "call_person",
            "status": "error",
            "person": person,
            "message": message,
            "error": (
                f"No phone number found for '{person}'. "
                "Provide an explicit phone number or add an entry to CONTACT_BOOK in .env."
            ),
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
        "person": person,
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
