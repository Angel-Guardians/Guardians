"""Risk score read routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session

from backend.api.schemas import RiskFactorRead, RiskSnapshotRead
from backend.db.session import get_session
from backend.services.risk_monitor import RiskMonitor

router = APIRouter()


def _to_read(snapshot) -> RiskSnapshotRead:
    return RiskSnapshotRead(
        score=snapshot.score,
        level=snapshot.level,
        severity_tier=snapshot.severity_tier.value,
        factors=[
            RiskFactorRead(
                name=f.name,
                score=f.score,
                weight=f.weight,
                detail=f.detail,
            )
            for f in snapshot.factors
        ],
        updated_at=snapshot.updated_at.isoformat(),
    )


@router.get("/current", response_model=RiskSnapshotRead)
def current_risk(
    request: Request,
    patient_id: int = Query(1),
    session: Session = Depends(get_session),
) -> RiskSnapshotRead:
    """Return the latest composite risk score for a patient."""
    monitor: RiskMonitor = request.app.state.risk_monitor
    snapshot, _changed = monitor.compute(session, patient_id)
    return _to_read(snapshot)
