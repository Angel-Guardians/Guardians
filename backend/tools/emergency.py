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
from dotenv import load_dotenv

load_dotenv()

CALL_LOG: list[dict[str, Any]] = []


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


def notify_caregiver(
    message: str,
    contact: str = "Sophie",
    phone: str = "",
) -> dict[str, Any]:
    """Call the caregiver and read the message aloud via Twilio <Say>.

    Falls back to a stub response when Twilio credentials are absent,
    so the agent loop works in dev/test without any external keys.
    """
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
            "contact": contact,
            "message": message,
            "note": "Set TWILIO_* in .env to enable real calls.",
        }
        CALL_LOG.append(event)
        return event

    to_number = os.getenv("TWILIO_TEST_TO_NUMBER")
    if not to_number:
        event = {
            "tool": "notify_caregiver",
            "status": "error",
            "contact": contact,
            "message": message,
            "error": "No phone number — set TWILIO_TEST_TO_NUMBER in .env.",
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
        "tool": "notify_caregiver",
        "status": "called",
        "channel": "voice",
        "contact": contact,
        "phone": to_number,
        "message": message,
        "call_sid": call.sid,
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
            description="Call the patient's emergency contact and read them a voice message. Use for urgent situations where the caregiver must be informed immediately.",
            parameters={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The message to read aloud to the caregiver."},
                    "contact": {"type": "string", "description": "Caregiver name (e.g. 'Sophie')."},
                    "phone": {"type": "string", "description": "Caregiver phone number in E.164 format (e.g. '+15555550111'). Leave blank to use the default emergency contact."},
                },
                "required": ["message"],
            },
        ),
        notify_caregiver,
    )
