"""Patient profile routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.api.schemas import PatientProfileRead, PatientProfileWrite
from backend.db.models import Patient
from backend.db.session import get_session
from backend.services.patient_profile import (
    PatientNotFoundError,
    get_patient_profile,
    update_patient_profile,
)

router = APIRouter()


@router.get("/", response_model=list[Patient])
def list_patients(session: Session = Depends(get_session)) -> list[Patient]:
    return list(session.exec(select(Patient)).all())


@router.post("/", response_model=PatientProfileRead, status_code=201)
def create_patient(
    body: PatientProfileWrite,
    session: Session = Depends(get_session),
) -> PatientProfileRead:
    """Create a new patient profile.

    Quick-create only needs name + age; the rest of `PatientProfileWrite`
    (conditions, contacts, medications, …) is optional and can be filled in later
    via PUT /patient/{id}/profile. Returns the full profile so the caller can
    switch to the new patient immediately.
    """
    patient = Patient(
        name=body.name,
        age=body.age,
        conditions=body.conditions,
        allergies=body.allergies,
        primary_language=body.primary_language,
        location=body.location,
        bio=body.bio,
        notes=body.notes,
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    assert patient.id is not None
    # Reuse the profile writer so any contacts/medications sent up are persisted
    # through the same path as edits.
    return update_patient_profile(session, patient.id, body)


@router.get("/{patient_id}/profile", response_model=PatientProfileRead)
def read_patient_profile(
    patient_id: int,
    session: Session = Depends(get_session),
) -> PatientProfileRead:
    try:
        return get_patient_profile(session, patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=404, detail="patient not found") from None


@router.put("/{patient_id}/profile", response_model=PatientProfileRead)
def write_patient_profile(
    patient_id: int,
    body: PatientProfileWrite,
    session: Session = Depends(get_session),
) -> PatientProfileRead:
    try:
        return update_patient_profile(session, patient_id, body)
    except PatientNotFoundError:
        raise HTTPException(status_code=404, detail="patient not found") from None


@router.get("/{patient_id}", response_model=Patient)
def get_patient(patient_id: int, session: Session = Depends(get_session)) -> Patient:
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="patient not found")
    return patient
