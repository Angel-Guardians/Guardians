"""Shared helpers for resolving the patient's emergency contacts from the DB.

The LLM chooses *who* to call by name or relationship (e.g. "Maria", "daughter",
"family_doctor"); these helpers turn that choice into concrete ``EmergencyContact``
rows — with their phone numbers — for the active patient. Phone numbers live only
in the database, never in the model's context or in env (apart from the 911 line).
"""
from __future__ import annotations

from sqlmodel import Session, select

from backend.db.models import EmergencyContact
from backend.persona import active_patient_id


def default_patient_id(session: Session) -> int | None:
    """The patient backing the active persona (GUARDIAN_PERSONA), or the first on file.

    Delegates to ``backend.persona`` so contact resolution always targets the same
    person the prompt persona describes — the model asks for "Sophie", and this
    looks her up under Matthew's record, not whoever happens to be patient #1.
    """
    return active_patient_id(session)


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
