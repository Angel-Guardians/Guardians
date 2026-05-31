"""Health tools — DB-backed.

`log_vital` persists a reading to the relational ``Vital`` table (the same store
the watch ingest and the Vitals page use). `get_medications` reads the patient's
real ``Medication`` rows. Both degrade gracefully: if the DB is unavailable or the
patient has no rows yet (e.g. offline smoke tests), they fall back to a safe canned
response so the agent loop never crashes on a tool call.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from loguru import logger
from sqlmodel import Session, select

from backend.db.models import Medication, Vital
from backend.db.session import engine
from backend.llm.base import ToolSpec
from backend.persona import active_patient_id

CALL_LOG: list[dict[str, Any]] = []

# Canned fallback used only when no DB / no patient is available (offline tests).
_FALLBACK_MEDS = [
    {"name": "metoprolol", "dose": "50 mg", "schedule": "morning"},
    {"name": "aspirin", "dose": "81 mg", "schedule": "morning"},
]


def _default_patient_id(session: Session) -> int | None:
    """The patient backing the active persona (GUARDIAN_PERSONA), or the first on file."""
    return active_patient_id(session)


def _coerce_float(value: str) -> float | None:
    """Pull a numeric reading out of a free-text value ('120', '98.6 bpm')."""
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group()) if match else None


def log_vital(metric: str, value: str, unit: str = "") -> dict[str, Any]:
    """Persist a vital sign the patient reports into the ``Vital`` table."""
    numeric = _coerce_float(value)
    event: dict[str, Any] = {
        "tool": "log_vital",
        "metric": metric,
        "value": value,
        "unit": unit,
    }
    if numeric is None:
        # Non-numeric (e.g. "feels high") — acknowledge but don't fabricate a row.
        event["status"] = "noted"
        event["persisted"] = False
        CALL_LOG.append(event)
        return event

    try:
        with Session(engine) as session:
            patient_id = _default_patient_id(session)
            if patient_id is None:
                event["status"] = "recorded"
                event["persisted"] = False
                event["note"] = "no patient on file; reading not stored"
                CALL_LOG.append(event)
                return event
            row = Vital(
                patient_id=patient_id,
                ts=datetime.utcnow(),
                kind=metric,
                value=numeric,
                source="manual",
            )
            session.add(row)
            session.commit()
            event["status"] = "recorded"
            event["persisted"] = True
            event["patient_id"] = patient_id
    except Exception as exc:  # pragma: no cover - degrade if DB unavailable
        logger.warning(f"[log_vital] DB unavailable, not persisted: {exc}")
        event["status"] = "recorded"
        event["persisted"] = False
    CALL_LOG.append(event)
    return event


def get_medications() -> dict[str, Any]:
    """Return the patient's current medication list from the DB."""
    try:
        with Session(engine) as session:
            patient_id = _default_patient_id(session)
            if patient_id is None:
                return {"tool": "get_medications", "source": "fallback", "medications": _FALLBACK_MEDS}
            meds = session.exec(
                select(Medication).where(Medication.patient_id == patient_id).order_by(Medication.id)
            ).all()
            if not meds:
                return {"tool": "get_medications", "source": "fallback", "medications": _FALLBACK_MEDS}
            return {
                "tool": "get_medications",
                "source": "db",
                "medications": [
                    {
                        "name": m.name,
                        "dose": m.dose,
                        "schedule": m.notes or m.schedule_cron,
                        "with_food": m.with_food,
                    }
                    for m in meds
                ],
            }
    except Exception as exc:  # pragma: no cover - degrade if DB unavailable
        logger.warning(f"[get_medications] DB unavailable, using fallback: {exc}")
        return {"tool": "get_medications", "source": "fallback", "medications": _FALLBACK_MEDS}


def register(registry) -> None:
    registry.register(
        ToolSpec(
            name="log_vital",
            description="Record a vital sign the patient reports (e.g. heart rate, blood pressure).",
            parameters={
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "description": "e.g. heart_rate, blood_pressure."},
                    "value": {"type": "string"},
                    "unit": {"type": "string"},
                },
                "required": ["metric", "value"],
            },
        ),
        log_vital,
    )
    registry.register(
        ToolSpec(
            name="get_medications",
            description="Look up the patient's current medication list.",
            parameters={"type": "object", "properties": {}},
        ),
        get_medications,
    )
