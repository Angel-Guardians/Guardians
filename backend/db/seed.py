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

# Demo phone numbers. Twilio trial accounts may only dial *verified* numbers, so
# every contact below uses one of the two numbers verified for this demo. Swap
# these two constants to re-point the whole demo at different phones.
#   FRIEND_PHONE  -> the friend's handset (priority-1 caregiver in both scenarios)
#   OWNER_PHONE   -> the demo owner's handset (also TWILIO_911_NUMBER in .env)
FRIEND_PHONE = "+14375533369"
OWNER_PHONE = "+14168379751"

ELEANOR_PROFILE = PatientProfileWrite(
    name="Eleanor",
    age=70,
    conditions=["cardiac history", "lives alone"],
    allergies=["penicillin"],
    primary_language="en",
    location="42 Maple Street, Toronto, ON",
    bio=(
        "Retired schoolteacher who loves gardening, crossword puzzles, and classic films. "
        "Enjoys quiet mornings with tea and the newspaper. Has a tabby cat named Biscuit. "
        "Volunteers at the local library on Thursdays when her health allows."
    ),
    notes="Post-hip-fracture recovery. Prefers calm reassurance during emergencies.",
    emergency_contacts=[
        EmergencyContactWrite(
            name="Sophie",
            relationship="caregiver",
            phone=FRIEND_PHONE,
            priority=1,
        ),
        EmergencyContactWrite(
            name="David",
            relationship="son",
            phone=OWNER_PHONE,
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


SARAH_PROFILE = PatientProfileWrite(
    name="Sarah",
    age=35,
    conditions=["physical disability", "wheelchair user", "mild depression"],
    allergies=[],
    primary_language="en",
    location="18 Birchwood Avenue, Vancouver, BC",
    bio=(
        "Graphic designer who works from home. Passionate about digital art, accessible travel, "
        "and adaptive sports — particularly wheelchair basketball and hand cycling. "
        "Enjoys cooking, podcasts, and weekend visits to local art galleries with friends."
    ),
    notes=(
        "Full-time wheelchair user. Has mild depression and attends regular psychologist sessions. "
        "Prefers to be spoken to as an independent adult. "
        "Avoid being overly cautious about her physical capability — she manages her own mobility."
    ),
    emergency_contacts=[
        EmergencyContactWrite(
            name="Liam",
            relationship="brother",
            phone=FRIEND_PHONE,
            priority=1,
        ),
        EmergencyContactWrite(
            name="Maya",
            relationship="close friend",
            phone=OWNER_PHONE,
            priority=2,
        ),
    ],
    medications=[
        ProfileMedicationWrite(
            name="Sertraline",
            dose="50 mg",
            schedule_cron="0 9 * * *",
            with_food=True,
            notes="Antidepressant — take with breakfast",
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
            location=ELEANOR_PROFILE.location,
            bio=ELEANOR_PROFILE.bio,
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


def upsert_sarah(session: Session) -> None:
    existing = session.exec(select(Patient).where(Patient.name == "Sarah")).first()
    if existing is None or existing.id is None:
        patient = Patient(
            name=SARAH_PROFILE.name,
            age=SARAH_PROFILE.age,
            conditions=SARAH_PROFILE.conditions,
            allergies=SARAH_PROFILE.allergies,
            primary_language=SARAH_PROFILE.primary_language,
            location=SARAH_PROFILE.location,
            bio=SARAH_PROFILE.bio,
            notes=SARAH_PROFILE.notes,
        )
        session.add(patient)
        session.commit()
        session.refresh(patient)
        patient_id = patient.id
        assert patient_id is not None
    else:
        patient_id = existing.id

    update_patient_profile(session, patient_id, SARAH_PROFILE)
    profile = get_patient_profile(session, patient_id)
    logger.info("Seeded patient #{}: {} ({})", profile.id, profile.name, profile.age)


def seed_if_empty() -> None:
    """Create demo patients when the database has no rows yet."""
    with Session(engine) as session:
        if session.exec(select(Patient)).first() is None:
            upsert_eleanor(session)
            upsert_sarah(session)


def seed_all() -> None:
    """Idempotent seed for CLI (`guardian-seed`)."""
    init_db()
    with Session(engine) as session:
        upsert_eleanor(session)
        upsert_sarah(session)
