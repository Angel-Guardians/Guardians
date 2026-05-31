"""Vitals ingestion + read routes.

POST /vitals/ingest  — batch insert readings from a wearable (e.g. Galaxy Watch).
GET  /vitals         — time-series read for the UI / verification.

The relational ``Vital`` table is the store here. In production these readings
would also fan out to InfluxDB and onto the event bus as ``VitalSampleEvent``;
for the current path, persisting to Postgres is enough to light up the Vitals
page and downstream queries.
"""
from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session, select

from backend.api.schemas import (
    FallEventRead,
    VitalIngestBatch,
    VitalIngestResult,
    VitalPoint,
    VitalSeries,
)
from backend.db.models import Vital
from backend.db.session import get_session
from backend.events.types import RiskScoreUpdatedEvent
from backend.services.fall_response import should_trigger, trigger_fall_response
from backend.services.risk_monitor import RiskMonitor

router = APIRouter()

_SINCE_RE = re.compile(r"^\s*(\d+)\s*([smhd])\s*$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _parse_since(since: str) -> timedelta:
    """Parse look-back windows like '24h', '60m', '7d'. Falls back to 24h."""
    match = _SINCE_RE.match(since or "")
    if not match:
        return timedelta(hours=24)
    amount = int(match.group(1))
    unit = match.group(2).lower()
    return timedelta(seconds=amount * _UNIT_SECONDS[unit])


def _to_naive_utc(ts: datetime) -> datetime:
    """Normalize to naive UTC to match the model's ``default_factory`` storage."""
    if ts.tzinfo is not None:
        return ts.astimezone(UTC).replace(tzinfo=None)
    return ts


async def _after_ingest(
    request: Request,
    session: Session,
    batch: VitalIngestBatch,
    rows: list[Vital],
) -> None:
    monitor: RiskMonitor = request.app.state.risk_monitor
    bus = request.app.state.event_bus
    guardian = request.app.state.guardian

    snapshot, changed = monitor.compute(session, batch.patient_id)
    if bus is not None and changed:
        factors = [
            {"name": f.name, "score": f.score, "weight": f.weight, "detail": f.detail}
            for f in snapshot.factors
        ]
        await bus.publish(
            RiskScoreUpdatedEvent(
                source="api.vitals",
                score=snapshot.score,
                level=snapshot.level,
                factors=factors,
                patient_id=batch.patient_id,
                severity=snapshot.severity_tier,
            ),
        )

    for row in rows:
        if should_trigger(batch.patient_id, row.kind):
            asyncio.create_task(
                trigger_fall_response(
                    guardian,
                    bus,
                    batch.patient_id,
                    row.kind,
                    row.value,
                ),
            )


@router.post("/ingest", response_model=VitalIngestResult)
async def ingest_vitals(
    batch: VitalIngestBatch,
    request: Request,
    session: Session = Depends(get_session),
) -> VitalIngestResult:
    """Accept a batch of readings from a wearable and persist them."""
    now = datetime.utcnow()
    rows = [
        Vital(
            patient_id=batch.patient_id,
            ts=_to_naive_utc(reading.ts) if reading.ts else now,
            kind=reading.kind,
            value=reading.value,
            source=batch.device,
        )
        for reading in batch.readings
    ]
    if rows:
        session.add_all(rows)
        session.commit()
        await _after_ingest(request, session, batch, rows)
    return VitalIngestResult(accepted=len(rows))


@router.get("", response_model=VitalSeries)
def read_vitals(
    kind: str = Query(..., description="hr | spo2 | steps | calories | ..."),
    since: str = Query("24h", description="Look-back window, e.g. 24h, 60m, 7d"),
    patient_id: int = Query(1),
    session: Session = Depends(get_session),
) -> VitalSeries:
    """Return a reading series for charting / verification."""
    cutoff = datetime.utcnow() - _parse_since(since)
    stmt = (
        select(Vital)
        .where(Vital.patient_id == patient_id)
        .where(Vital.kind == kind)
        .where(Vital.ts >= cutoff)
        .order_by(Vital.ts)
    )
    rows = session.exec(stmt).all()
    points = [VitalPoint(ts=row.ts.isoformat(), value=row.value) for row in rows]
    return VitalSeries(kind=kind, points=points)


@router.get("/falls", response_model=list[FallEventRead])
def list_falls(
    since: str = Query("24h", description="Look-back window, e.g. 24h, 60m, 7d"),
    patient_id: int = Query(1),
    session: Session = Depends(get_session),
) -> list[FallEventRead]:
    """Recent fall events (suspected / confirmed / cancelled), newest first."""
    cutoff = datetime.utcnow() - _parse_since(since)
    stmt = (
        select(Vital)
        .where(Vital.patient_id == patient_id)
        .where(Vital.kind.like("fall%"))
        .where(Vital.ts >= cutoff)
        .order_by(Vital.ts.desc())
    )
    rows = session.exec(stmt).all()
    return [
        FallEventRead(
            kind=row.kind,
            value=row.value,
            ts=row.ts.isoformat() + "Z",
            source=row.source,
        )
        for row in rows
    ]
