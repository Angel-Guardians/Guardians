"""The active patient for the current turn.

Tools resolve patient data (emergency contacts, medications, consent) from the DB.
Historically they fell back to "the first patient on file", so every tool call hit
patient #1 regardless of which profile the UI had selected — meaning a caregiver
call placed during Sarah's scenario still dialled Eleanor's contacts.

GuardianAgent.turn() sets this ContextVar to the patient it is serving before it
invokes the graph. The whole graph + tool loop runs synchronously in the same
worker thread, so the value is visible to every tool for the duration of the turn.
When unset (e.g. a bare tool call in a test), the tools fall back to the first
patient exactly as before.
"""
from __future__ import annotations

from contextvars import ContextVar

_active_patient_id: ContextVar[int | None] = ContextVar("active_patient_id", default=None)


def set_active_patient(patient_id: int | None) -> None:
    """Mark which patient the current turn is serving."""
    _active_patient_id.set(patient_id)


def get_active_patient() -> int | None:
    """The patient the current turn is serving, or None if not set."""
    return _active_patient_id.get()
