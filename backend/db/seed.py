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

MATTHEW_PROFILE = PatientProfileWrite(
    name="Matthew",
    age=78,
    conditions=[
        "atrial fibrillation",
        "prior heart attack with stents",
        "mild heart failure",
        "lives alone",
    ],
    allergies=[],
    primary_language="en",
    location="200 Wellesley Street East, Apt 1407, Toronto, ON M4X 1G7",
    bio=(
        "Retired civil engineer who still tinkers with model trains and reads military "
        "history. Widower; his late wife Joan passed three years ago. Enjoys jazz records, "
        "morning walks when his energy allows, and weekly video calls with his grandchildren."
    ),
    notes=(
        "On a blood thinner (apixaban) — falls and head injuries carry a high bleeding risk, "
        "so any fall is treated seriously. Prefers calm, plain-spoken reassurance. "
        "Sophie, a nurse in the same building (CPR/AED-trained), is the first to call; "
        "his daughter Claire in Ottawa is notified after Sophie."
    ),
    emergency_contacts=[
        # Primary support is Sophie — must match the Matthew persona block in
        # backend/agents/prompts/_base.py so notify_caregiver(["Sophie"]) resolves.
        EmergencyContactWrite(
            name="Sophie",
            relationship="neighbor_nurse",
            phone="+1 (416) 555-0188",
            priority=1,
        ),
        EmergencyContactWrite(
            name="Claire",
            relationship="daughter",
            phone="+1 (613) 555-0173",
            priority=2,
        ),
    ],
    medications=[
        ProfileMedicationWrite(
            name="Apixaban",
            dose="2.5 mg",
            schedule_cron="0 8,20 * * *",
            with_food=False,
            notes="Blood thinner — twice daily, morning and evening",
        ),
        ProfileMedicationWrite(
            name="Metoprolol",
            dose="50 mg",
            schedule_cron="0 8,20 * * *",
            with_food=True,
            notes="Beta blocker — rate control, twice daily with meals",
        ),
        ProfileMedicationWrite(
            name="Atorvastatin",
            dose="40 mg",
            schedule_cron="0 20 * * *",
            with_food=False,
            notes="Statin — evening",
        ),
        ProfileMedicationWrite(
            name="Furosemide",
            dose="20 mg",
            schedule_cron="0 8 * * *",
            with_food=False,
            notes="Diuretic for heart failure — morning",
        ),
    ],
)


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
        # Primary support is her sister Amara — must match the Sarah persona block
        # in backend/agents/prompts/_base.py so notify_caregiver(["Amara"]) resolves.
        EmergencyContactWrite(
            name="Amara",
            relationship="sister",
            phone="+1 (555) 555-0203",
            priority=1,
        ),
        EmergencyContactWrite(
            name="Dr. Patel",
            relationship="psychologist",
            phone="+1 (555) 555-0201",
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


def upsert_matthew(session: Session) -> None:
    existing = session.exec(select(Patient).where(Patient.name == "Matthew")).first()
    if existing is None or existing.id is None:
        patient = Patient(
            name=MATTHEW_PROFILE.name,
            age=MATTHEW_PROFILE.age,
            conditions=MATTHEW_PROFILE.conditions,
            allergies=MATTHEW_PROFILE.allergies,
            primary_language=MATTHEW_PROFILE.primary_language,
            location=MATTHEW_PROFILE.location,
            bio=MATTHEW_PROFILE.bio,
            notes=MATTHEW_PROFILE.notes,
        )
        session.add(patient)
        session.commit()
        session.refresh(patient)
        patient_id = patient.id
        assert patient_id is not None
    else:
        patient_id = existing.id

    update_patient_profile(session, patient_id, MATTHEW_PROFILE)
    profile = get_patient_profile(session, patient_id)
    logger.info("Seeded patient #{}: {} ({})", profile.id, profile.name, profile.age)


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
            upsert_matthew(session)
            upsert_eleanor(session)
            upsert_sarah(session)


def seed_all() -> None:
    """Idempotent seed for CLI (`guardian-seed`)."""
    init_db()
    with Session(engine) as session:
        upsert_matthew(session)
        upsert_eleanor(session)
        upsert_sarah(session)
