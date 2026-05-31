"""Read/write Patient + EmergencyContact + Medication as one profile."""
from __future__ import annotations

from sqlmodel import Session, select

from backend.api.schemas import (
    EmergencyContactRead,
    PatientProfileRead,
    PatientProfileWrite,
    ProfileMedicationRead,
)
from backend.db.models import EmergencyContact, Medication, Patient


class PatientNotFoundError(LookupError):
    """Raised when a patient id does not exist."""


def get_patient_profile(session: Session, patient_id: int) -> PatientProfileRead:
    patient = session.get(Patient, patient_id)
    if patient is None or patient.id is None:
        raise PatientNotFoundError(patient_id)

    contacts = list(
        session.exec(
            select(EmergencyContact)
            .where(EmergencyContact.patient_id == patient_id)
            .order_by(EmergencyContact.priority, EmergencyContact.id)  # type: ignore[arg-type]
        ).all()
    )
    medications = list(
        session.exec(
            select(Medication)
            .where(Medication.patient_id == patient_id)
            .order_by(Medication.id)  # type: ignore[arg-type]
        ).all()
    )

    return PatientProfileRead(
        id=patient.id,
        name=patient.name,
        age=patient.age,
        conditions=patient.conditions,
        allergies=patient.allergies,
        primary_language=patient.primary_language,
        location=patient.location,
        bio=patient.bio,
        notes=patient.notes,
        emergency_contacts=[
            EmergencyContactRead.model_validate(c, from_attributes=True) for c in contacts
        ],
        medications=[
            ProfileMedicationRead.model_validate(m, from_attributes=True) for m in medications
        ],
    )


def update_patient_profile(
    session: Session,
    patient_id: int,
    data: PatientProfileWrite,
) -> PatientProfileRead:
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise PatientNotFoundError(patient_id)

    patient.name = data.name
    patient.age = data.age
    patient.conditions = data.conditions
    patient.allergies = data.allergies
    patient.primary_language = data.primary_language
    patient.location = data.location
    patient.bio = data.bio
    patient.notes = data.notes

    for contact in session.exec(
        select(EmergencyContact).where(EmergencyContact.patient_id == patient_id)
    ).all():
        session.delete(contact)

    for medication in session.exec(
        select(Medication).where(Medication.patient_id == patient_id)
    ).all():
        session.delete(medication)

    session.flush()

    for contact in data.emergency_contacts:
        session.add(
            EmergencyContact(
                patient_id=patient_id,
                name=contact.name,
                relationship=contact.relationship,
                phone=contact.phone,
                priority=contact.priority,
            )
        )

    for medication in data.medications:
        session.add(
            Medication(
                patient_id=patient_id,
                name=medication.name,
                dose=medication.dose,
                schedule_cron=medication.schedule_cron,
                with_food=medication.with_food,
                notes=medication.notes,
            )
        )

    session.commit()
    session.refresh(patient)
    return get_patient_profile(session, patient_id)
