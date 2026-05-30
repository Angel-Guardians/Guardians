"""Demo patient seed data for local development and tests."""
from __future__ import annotations

from loguru import logger
from sqlmodel import Session, select

from backend.api.schemas import (
    EmergencyContactWrite,
    PatientProfileWrite,
    ProfileMedicationWrite,
)
from backend.db.models import Patient
from backend.db.session import engine, init_db
from backend.services.patient_profile import get_patient_profile, update_patient_profile

ELEANOR_PROFILE = PatientProfileWrite(
    name="Eleanor",
    age=70,
    conditions=["cardiac history", "lives alone"],
    allergies=["penicillin"],
    primary_language="en",
    notes="Post-hip-fracture recovery. Prefers calm reassurance during emergencies.",
    emergency_contacts=[
        EmergencyContactWrite(
            name="Maria",
            relationship="daughter",
            phone="+1 (555) 555-0111",
            priority=1,
        ),
        EmergencyContactWrite(
            name="Dr. Adeyemi",
            relationship="family_doctor",
            phone="+1 (555) 555-0122",
            priority=2,
        ),
    ],
    medications=[
        ProfileMedicationWrite(
            name="Lisinopril",
            dose="10 mg",
            schedule_cron="0 8 * * *",
            with_food=False,
            notes="Blood pressure — morning",
        ),
        ProfileMedicationWrite(
            name="Metoprolol",
            dose="25 mg",
            schedule_cron="0 8,20 * * *",
            with_food=True,
            notes="Twice daily with meals",
        ),
    ],
)


def upsert_eleanor(session: Session) -> None:
    existing = session.exec(select(Patient).where(Patient.name == "Eleanor")).first()
    if existing is None or existing.id is None:
        patient = Patient(
            name=ELEANOR_PROFILE.name,
            age=ELEANOR_PROFILE.age,
            conditions=ELEANOR_PROFILE.conditions,
            allergies=ELEANOR_PROFILE.allergies,
            primary_language=ELEANOR_PROFILE.primary_language,
            notes=ELEANOR_PROFILE.notes,
        )
        session.add(patient)
        session.commit()
        session.refresh(patient)
        patient_id = patient.id
        assert patient_id is not None
    else:
        patient_id = existing.id

    update_patient_profile(session, patient_id, ELEANOR_PROFILE)
    profile = get_patient_profile(session, patient_id)
    logger.info("Seeded patient #{}: {} ({})", profile.id, profile.name, profile.age)


def seed_if_empty() -> None:
    """Create demo patients when the database has no rows yet."""
    with Session(engine) as session:
        if session.exec(select(Patient)).first() is None:
            upsert_eleanor(session)


def seed_all() -> None:
    """Idempotent seed for CLI (`guardian-seed`)."""
    init_db()
    with Session(engine) as session:
        upsert_eleanor(session)
