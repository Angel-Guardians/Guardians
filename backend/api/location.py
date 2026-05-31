"""Location track routes.

POST /location/ingest  — batch insert GPS samples from the wearable.
GET  /location         — recent position track for the map / verification.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from backend.api.schemas import LocationBatch, LocationRead, VitalIngestResult
from backend.db.models import Location
from backend.db.session import get_session

router = APIRouter()

_SINCE_RE = re.compile(r"^\s*(\d+)\s*([smhd])\s*$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _parse_since(since: str) -> timedelta:
    match = _SINCE_RE.match(since or "")
    if not match:
        return timedelta(hours=24)
    return timedelta(seconds=int(match.group(1)) * _UNIT_SECONDS[match.group(2).lower()])


def _to_naive_utc(ts: datetime) -> datetime:
    if ts.tzinfo is not None:
        return ts.astimezone(UTC).replace(tzinfo=None)
    return ts


@router.post("/ingest", response_model=VitalIngestResult)
def ingest_locations(
    batch: LocationBatch,
    session: Session = Depends(get_session),
) -> VitalIngestResult:
    """Accept a batch of GPS samples from the wearable and persist them."""
    now = datetime.utcnow()
    rows = [
        Location(
            patient_id=batch.patient_id,
            ts=_to_naive_utc(point.ts) if point.ts else now,
            lat=point.lat,
            lng=point.lng,
            accuracy=point.accuracy,
            source=batch.device,
        )
        for point in batch.points
    ]
    if rows:
        session.add_all(rows)
        session.commit()
    return VitalIngestResult(accepted=len(rows))


@router.get("", response_model=list[LocationRead])
def read_locations(
    since: str = Query("24h", description="Look-back window, e.g. 24h, 60m, 7d"),
    patient_id: int = Query(1),
    limit: int = Query(1000, le=5000),
    session: Session = Depends(get_session),
) -> list[LocationRead]:
    """Return the recent position track, newest first."""
    cutoff = datetime.utcnow() - _parse_since(since)
    stmt = (
        select(Location)
        .where(Location.patient_id == patient_id)
        .where(Location.ts >= cutoff)
        .order_by(Location.ts.desc())
        .limit(limit)
    )
    rows = session.exec(stmt).all()
    return [
        LocationRead(
            lat=row.lat,
            lng=row.lng,
            accuracy=row.accuracy,
            ts=row.ts.isoformat() + "Z",
        )
        for row in rows
    ]
