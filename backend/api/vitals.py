"""Vitals ingest + read-back. Implements the Wear OS watch contract.

POST /vitals/ingest   <- batch upload from the watch (every 60s)
GET  /vitals          -> series for the frontend Vitals chart

See watch/README.md "Backend API contract".
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.db.models import Vital
from backend.db.session import get_session

router = APIRouter()

_SINCE_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


class Reading(BaseModel):
    kind: str
    value: float
    ts: datetime | None = None


class IngestRequest(BaseModel):
    patient_id: int = 1
    device: str = "galaxy_watch"
    readings: list[Reading]


def _parse_since(since: str) -> timedelta:
    m = re.fullmatch(r"(\d+)([smhd])", since.strip())
    if not m:
        return timedelta(hours=24)
    return timedelta(seconds=int(m.group(1)) * _SINCE_UNITS[m.group(2)])


@router.post("/ingest")
def ingest(body: IngestRequest, session: Session = Depends(get_session)) -> dict[str, int]:
    accepted = 0
    for r in body.readings:
        session.add(
            Vital(
                patient_id=body.patient_id,
                ts=r.ts or datetime.utcnow(),
                kind=r.kind,
                value=r.value,
                source=body.device,
            )
        )
        accepted += 1
    session.commit()
    return {"accepted": accepted}


@router.get("")
def read_vitals(
    kind: str = Query("hr"),
    since: str = Query("24h"),
    patient_id: int = Query(1),
    session: Session = Depends(get_session),
) -> dict:
    cutoff = datetime.utcnow() - _parse_since(since)
    rows = session.exec(
        select(Vital)
        .where(Vital.patient_id == patient_id)
        .where(Vital.kind == kind)
        .where(Vital.ts >= cutoff)
        .order_by(Vital.ts)  # type: ignore[arg-type]
    ).all()
    return {
        "kind": kind,
        "points": [{"ts": v.ts.isoformat(), "value": v.value} for v in rows],
    }
