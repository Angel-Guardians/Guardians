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
