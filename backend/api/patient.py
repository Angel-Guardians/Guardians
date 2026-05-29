"""Patient profile routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.db.models import Patient
from backend.db.session import get_session

router = APIRouter()


@router.get("/{patient_id}", response_model=Patient)
def get_patient(patient_id: int, session: Session = Depends(get_session)) -> Patient:
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="patient not found")
    return patient


@router.get("/", response_model=list[Patient])
def list_patients(session: Session = Depends(get_session)) -> list[Patient]:
    return list(session.exec(select(Patient)).all())
