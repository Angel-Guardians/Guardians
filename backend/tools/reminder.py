"""Reminder tools — DB-backed.

`get_schedule` builds today's medication times from each ``Medication``'s
``schedule_cron`` (minute + hour fields). `mark_med_taken` records adherence as a
``ReminderIntake`` row linked to the medication. Both degrade gracefully to a
canned response when the DB is unavailable or the patient is unseeded, so the
agent loop keeps working offline (e.g. smoke tests).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger
from sqlmodel import Session, select

from backend.db.models import Medication, Patient, ReminderIntake
from backend.db.session import engine
from backend.llm.base import ToolSpec

CALL_LOG: list[dict[str, Any]] = []

_FALLBACK_SCHEDULE = [
    {"time": "08:00", "what": "morning medication"},
    {"time": "12:30", "what": "lunch"},
    {"time": "15:00", "what": "call with family"},
]


def _default_patient_id(session: Session) -> int | None:
    from backend.tools._active_patient import get_active_patient

    active = get_active_patient()
    if active is not None:
        return active
    return session.exec(select(Patient.id).order_by(Patient.id)).first()


def _cron_field(field: str, default: int) -> list[int]:
    """Expand a minute/hour cron field into concrete values.

    Handles '*', single values, and comma lists ('8,20'). '*' in the hour field
    can't be enumerated meaningfully for a schedule, so it collapses to `default`.
    """
    if field == "*":
        return [default]
    out: list[int] = []
    for part in field.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out or [default]


def _cron_times(cron: str) -> list[str]:
    """Return the 'HH:MM' clock times a cron expression fires at today."""
    fields = cron.split()
    if len(fields) < 2:
        return []
    minutes = _cron_field(fields[0], 0)
    hours = _cron_field(fields[1], 0)
    times = {f"{h:02d}:{m:02d}" for h in hours for m in minutes}
    return sorted(times)


def get_schedule() -> dict[str, Any]:
    """Return today's medication times, derived from each med's cron schedule."""
    try:
        with Session(engine) as session:
            patient_id = _default_patient_id(session)
            if patient_id is None:
                return {"tool": "get_schedule", "source": "fallback", "items": _FALLBACK_SCHEDULE}
            meds = session.exec(
                select(Medication).where(Medication.patient_id == patient_id).order_by(Medication.id)
            ).all()
            if not meds:
                return {"tool": "get_schedule", "source": "fallback", "items": _FALLBACK_SCHEDULE}
            items: list[dict[str, str]] = []
            for med in meds:
                what = f"{med.name} {med.dose}".strip()
                for t in _cron_times(med.schedule_cron) or ["as scheduled"]:
                    items.append({"time": t, "what": what})
            items.sort(key=lambda i: i["time"])
            return {"tool": "get_schedule", "source": "db", "items": items}
    except Exception as exc:  # pragma: no cover - degrade if DB unavailable
        logger.warning(f"[get_schedule] DB unavailable, using fallback: {exc}")
        return {"tool": "get_schedule", "source": "fallback", "items": _FALLBACK_SCHEDULE}


def mark_med_taken(medication: str) -> dict[str, Any]:
    """Record that the patient took a medication (a ``ReminderIntake`` row)."""
    event: dict[str, Any] = {
        "tool": "mark_med_taken",
        "status": "acknowledged",
        "medication": medication,
    }
    try:
        with Session(engine) as session:
            patient_id = _default_patient_id(session)
            med = None
            if patient_id is not None:
                med = session.exec(
                    select(Medication)
                    .where(Medication.patient_id == patient_id)
                    .where(Medication.name.ilike(medication))  # type: ignore[attr-defined]
                ).first()
            if med is None or med.id is None:
                event["persisted"] = False
                event["note"] = f"'{medication}' not found in the regimen; acknowledged only"
                CALL_LOG.append(event)
                return event
            now = datetime.utcnow()
            session.add(
                ReminderIntake(
                    medication_id=med.id,
                    scheduled_for=now,
                    confirmed_at=now,
                    method="voice",
                )
            )
            session.commit()
            event["persisted"] = True
            event["medication"] = med.name
    except Exception as exc:  # pragma: no cover - degrade if DB unavailable
        logger.warning(f"[mark_med_taken] DB unavailable, not persisted: {exc}")
        event["persisted"] = False
    CALL_LOG.append(event)
    return event


def register(registry) -> None:
    registry.register(
        ToolSpec(
            name="get_schedule",
            description="Look up the patient's schedule and medication times for today.",
            parameters={"type": "object", "properties": {}},
        ),
        get_schedule,
    )
    registry.register(
        ToolSpec(
            name="mark_med_taken",
            description="Record that the patient has taken a medication.",
            parameters={
                "type": "object",
                "properties": {"medication": {"type": "string"}},
                "required": ["medication"],
            },
        ),
        mark_med_taken,
    )
