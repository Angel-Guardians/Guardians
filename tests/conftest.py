"""Shared pytest fixtures.

Reusable across unit + scenario tests:
  - ephemeral Postgres database (testcontainers)
  - mocked event bus
  - seeded Eleanor profile
  - fake LLM that echoes a canned response
  - fake TTS that records utterances instead of speaking
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, create_engine
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """Spin up an ephemeral Postgres for the whole test session."""
    with PostgresContainer("postgres:17", driver="psycopg") as pg:
        yield pg.get_connection_url()


@pytest.fixture
def db_session(postgres_url: str) -> Iterator[Session]:
    """Postgres-backed session with a fresh schema per test."""
    engine = create_engine(postgres_url, echo=False, pool_pre_ping=True)
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def event_bus():
    """Fresh EventBus per test."""
    from backend.events.bus import EventBus

    return EventBus()


@pytest.fixture
def eleanor(db_session: Session):
    """Seeded Eleanor (70, cardiac, lives alone) for scenario tests."""
    from backend.db.models import EmergencyContact, Patient

    patient = Patient(
        name="Eleanor",
        age=70,
        conditions=["cardiac"],
        allergies=["penicillin"],
        notes="Lives alone.",
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    db_session.add_all(
        [
            EmergencyContact(
                patient_id=patient.id,
                name="Sophie",
                relationship="daughter",
                phone="+15555550111",
                priority=1,
            ),
            EmergencyContact(
                patient_id=patient.id,
                name="Dr. Adeyemi",
                relationship="family_doctor",
                phone="+15555550122",
                priority=2,
            ),
        ]
    )
    db_session.commit()

    return patient
