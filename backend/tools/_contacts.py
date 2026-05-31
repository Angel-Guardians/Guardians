"""Shared helpers for resolving the patient's emergency contacts from the DB.

The LLM chooses *who* to call by name or relationship (e.g. "Maria", "daughter",
"family_doctor"); these helpers turn that choice into concrete ``EmergencyContact``
rows — with their phone numbers — for the active patient. Phone numbers live only
in the database, never in the model's context or in env (apart from the 911 line).
"""
from __future__ import annotations

from sqlmodel import Session, select

from backend.db.models import EmergencyContact, Patient


def default_patient_id(session: Session) -> int | None:
    """The single-home patient: the first patient on file, or None if unseeded."""
    return session.exec(select(Patient.id).order_by(Patient.id)).first()


def _all_contacts(session: Session, patient_id: int) -> list[EmergencyContact]:
    return list(
        session.exec(
            select(EmergencyContact)
            .where(EmergencyContact.patient_id == patient_id)
            .order_by(EmergencyContact.priority, EmergencyContact.id)  # type: ignore[arg-type]
        ).all()
    )


def resolve_contacts(
    session: Session,
    patient_id: int,
    requested: list[str] | None,
) -> list[EmergencyContact]:
    """Map the LLM's chosen names/relationships to ``EmergencyContact`` rows.

    Matching is case-insensitive and substring-based against both ``name`` and
    ``relationship`` (so "maria", "daughter", or "Dr. Adeyemi" all resolve). When
    nothing is requested, defaults to the single highest-priority contact. Results
    are de-duplicated and returned in priority order.
    """
    contacts = _all_contacts(session, patient_id)
    if not contacts:
        return []

    # Default: the priority-1 contact (contacts are already priority-ordered).
    if not requested:
        return [contacts[0]]

    matched: dict[int, EmergencyContact] = {}
    for term in requested:
        needle = (term or "").strip().lower()
        if not needle:
            continue
        for c in contacts:
            if c.id is None:
                continue
            if needle in c.name.lower() or needle in c.relationship.lower():
                matched[c.id] = c

    return sorted(matched.values(), key=lambda c: (c.priority, c.id or 0))
