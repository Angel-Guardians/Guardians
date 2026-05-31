"""Unit tests for the cross-cutting tool decorators.

These are Docker-free: the decorators read/write the global SQLModel engine, so we
point that engine at a fresh in-memory SQLite DB (via monkeypatch) and seed a
single patient. No testcontainers / Postgres required.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select


@pytest.fixture
def sqlite_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """Repoint the modules that open sessions at an in-memory SQLite engine.

    StaticPool keeps a single connection alive so the in-memory DB persists
    across the separate ``Session(engine)`` blocks the decorators open.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    import backend.db.session as db_session
    import backend.events.log as event_log

    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(event_log, "engine", engine)

    # Seed a single patient so consent/patient lookups resolve.
    from backend.db.models import Patient

    with Session(engine) as session:
        session.add(Patient(name="Eleanor", age=70))
        session.commit()

    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _clear_idempotency() -> Iterator[None]:
    from backend.tools.decorators import reset_idempotency

    reset_idempotency()
    yield
    reset_idempotency()


def test_consent_check_blocks_egress_when_denied(sqlite_engine: object) -> None:
    from backend.db.models import ConsentMatrix, Patient
    from backend.tools.decorators import consent_check

    calls: list[str] = []

    @consent_check(recipient="family", data_category="status_update")
    def notify(message: str) -> dict:
        calls.append(message)
        return {"tool": "notify", "status": "called"}

    # No matrix row → fail-open (allowed).
    assert notify(message="hi")["status"] == "called"
    assert calls == ["hi"]

    # Set the pair to 'never' → blocked, underlying fn not invoked.
    with Session(sqlite_engine) as session:
        pid = session.exec(select(Patient.id)).first()
        session.add(
            ConsentMatrix(
                patient_id=pid,
                recipient="family",
                data_category="status_update",
                mode="never",
            )
        )
        session.commit()

    result = notify(message="hi again")
    assert result["status"] == "blocked_by_consent"
    assert calls == ["hi"], "blocked call must not reach the underlying tool"


def test_idempotent_dedupes_within_window(sqlite_engine: object) -> None:
    from backend.tools.decorators import idempotent

    calls: list[str] = []

    @idempotent(window_seconds=60)
    def dial(reason: str) -> dict:
        calls.append(reason)
        return {"tool": "dial", "status": "called"}

    first = dial(reason="fall")
    second = dial(reason="fall")  # identical within window → suppressed
    third = dial(reason="different")  # distinct args → fires

    assert first["status"] == "called"
    assert second["status"] == "duplicate_suppressed"
    assert third["status"] == "called"
    assert calls == ["fall", "different"]


def test_audit_log_writes_tool_invocation_row(sqlite_engine: object) -> None:
    from backend.db.models import EventLogEntry
    from backend.tools.decorators import audit_log

    @audit_log
    def do_thing(x: int) -> dict:
        return {"tool": "do_thing", "status": "ok", "echo": x}

    do_thing(x=7)

    with Session(sqlite_engine) as session:
        rows = session.exec(
            select(EventLogEntry).where(EventLogEntry.event_type == "tool_invocation")
        ).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.source == "tool.do_thing"
    assert row.payload["args"] == {"x": 7}
    assert row.payload["result"]["status"] == "ok"


def test_audit_log_records_failure_and_reraises(sqlite_engine: object) -> None:
    from backend.db.models import EventLogEntry
    from backend.tools.decorators import audit_log

    @audit_log
    def boom() -> dict:
        raise ValueError("kaboom")

    with pytest.raises(ValueError):
        boom()

    with Session(sqlite_engine) as session:
        rows = session.exec(select(EventLogEntry)).all()
    assert len(rows) == 1
    assert rows[0].reason == "tool raised"
    assert "kaboom" in rows[0].payload["error"]
