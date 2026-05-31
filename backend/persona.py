"""Active demo persona — the single source of truth (set by GUARDIAN_PERSONA).

Both layers resolve the patient through this module, so the person the model is
*told* about (the prompt persona in ``agents/prompts/_base.py``) and the person
the tools *act on* (contacts, medications, schedule looked up from the DB) can
never drift apart.

Switch persona with the ``GUARDIAN_PERSONA`` env var and restart:

    GUARDIAN_PERSONA=matthew   (default — Scenario 1, the night-fall demo)
    GUARDIAN_PERSONA=sarah     (Scenario 2, the proactive-companion demo)

The persona is fixed for the lifetime of the process (it is read once at import),
which is exactly why switching it is an env change + restart, not a code edit.
"""
from __future__ import annotations

import os

from sqlmodel import Session, select

from backend.db.models import Patient

# Resolved once at import; the persona is fixed for the process lifetime.
ACTIVE_PERSONA: str = os.environ.get("GUARDIAN_PERSONA", "matthew").strip().lower()

# persona key -> the DB ``Patient.name`` that carries its contacts, meds, schedule.
# This is the bridge that keeps the prompt persona and the tool data in lockstep.
PERSONA_PATIENT_NAME: dict[str, str] = {
    "matthew": "Matthew",
    "sarah": "Sarah",
    "eleanor": "Eleanor",
}


def active_patient_name() -> str:
    """DB name of the patient backing the active persona."""
    return PERSONA_PATIENT_NAME.get(ACTIVE_PERSONA, "Matthew")


def active_patient_id(session: Session) -> int | None:
    """Resolve the active persona to a patient id.

    Matches the persona's patient by name; if that patient isn't seeded yet,
    falls back to the first patient on file so tools still function rather than
    erroring. Every tool that needs "the current patient" goes through here, so
    they all act on whoever the prompt persona describes.
    """
    name = active_patient_name()
    pid = session.exec(
        select(Patient.id).where(Patient.name == name).order_by(Patient.id)
    ).first()
    if pid is None:
        pid = session.exec(select(Patient.id).order_by(Patient.id)).first()
    return pid
