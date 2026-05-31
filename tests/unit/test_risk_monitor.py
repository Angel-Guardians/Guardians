"""Unit tests for weighted risk scoring and fall override."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.db.models import Patient, SeverityTier, Vital
from backend.orchestrator.risk_classifier import RiskClassifier
from backend.services.fall_response import should_trigger
from backend.services.risk_monitor import RiskMonitor, compute_risk


@pytest.fixture
def sqlite_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            patient = Patient(name="Eleanor", age=70, conditions=["cardiac"])
            session.add(patient)
            session.commit()
            session.refresh(patient)
            yield session
    finally:
        engine.dispose()


def _patient_id(session: Session) -> int:
    patient = session.exec(select(Patient)).first()
    assert patient and patient.id is not None
    return patient.id


def _add_vital(
    session: Session,
    patient_id: int,
    kind: str,
    value: float,
    *,
    minutes_ago: int = 1,
) -> None:
    session.add(
        Vital(
            patient_id=patient_id,
            kind=kind,
            value=value,
            source="test",
            ts=datetime.utcnow() - timedelta(minutes=minutes_ago),
        ),
    )
    session.commit()


def test_normal_vitals_low_risk(sqlite_session: Session) -> None:
    pid = _patient_id(sqlite_session)
    _add_vital(sqlite_session, pid, "hr", 72)
    _add_vital(sqlite_session, pid, "spo2", 98)

    snapshot = compute_risk(sqlite_session, pid)

    assert snapshot.level == "low"
    assert snapshot.score < 30
    assert snapshot.severity_tier == SeverityTier.WHISPER


def test_elevated_hr_and_low_spo2_raise_score(sqlite_session: Session) -> None:
    pid = _patient_id(sqlite_session)
    _add_vital(sqlite_session, pid, "hr", 130)
    _add_vital(sqlite_session, pid, "spo2", 89)

    snapshot = compute_risk(sqlite_session, pid)

    assert snapshot.score >= 30
    assert snapshot.level in ("moderate", "high", "critical")


def test_fall_suspected_forces_critical(sqlite_session: Session) -> None:
    pid = _patient_id(sqlite_session)
    _add_vital(sqlite_session, pid, "hr", 72)
    _add_vital(sqlite_session, pid, "fall_suspected", 3.2)

    snapshot = compute_risk(sqlite_session, pid)

    assert snapshot.level == "critical"
    assert snapshot.score == 100
    assert snapshot.severity_tier == SeverityTier.CALL
    assert any(f.name == "Fall detected" for f in snapshot.factors)


def test_fall_cancelled_clears_override(sqlite_session: Session) -> None:
    pid = _patient_id(sqlite_session)
    _add_vital(sqlite_session, pid, "fall_suspected", 3.0, minutes_ago=5)
    _add_vital(sqlite_session, pid, "fall_cancelled", 0.0, minutes_ago=1)
    _add_vital(sqlite_session, pid, "hr", 75, minutes_ago=1)
    _add_vital(sqlite_session, pid, "spo2", 97, minutes_ago=1)

    snapshot = compute_risk(sqlite_session, pid)

    assert snapshot.level == "low"
    assert not any(f.name == "Fall detected" for f in snapshot.factors)


def test_risk_monitor_tracks_changes(sqlite_session: Session) -> None:
    pid = _patient_id(sqlite_session)
    _add_vital(sqlite_session, pid, "hr", 75)
    _add_vital(sqlite_session, pid, "spo2", 97)
    monitor = RiskMonitor()

    snap1, changed1 = monitor.compute(sqlite_session, pid)
    assert changed1 is True
    assert snap1.level == "low"

    snap2, changed2 = monitor.compute(sqlite_session, pid)
    assert changed2 is False

    _add_vital(sqlite_session, pid, "fall_suspected", 2.8)
    snap3, changed3 = monitor.compute(sqlite_session, pid)
    assert changed3 is True
    assert snap3.level == "critical"


@pytest.mark.asyncio
async def test_risk_classifier_fall_vital() -> None:
    from backend.events.types import VitalSampleEvent

    classifier = RiskClassifier()
    tier = await classifier.classify(
        VitalSampleEvent(source="test", kind="fall_suspected", value=3.0, device="watch"),
    )
    assert tier == SeverityTier.CALL


def test_fall_trigger_dedup() -> None:
    import backend.services.fall_response as fr

    fr._last_fired.clear()
    assert should_trigger(1, "fall_suspected") is True
    assert should_trigger(1, "fall_suspected") is False
    assert should_trigger(1, "fall_cancelled") is False
