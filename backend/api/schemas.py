"""Request/response schemas for the HTTP API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EmergencyContactRead(BaseModel):
    id: int
    name: str
    relationship: str
    phone: str
    priority: int


class EmergencyContactWrite(BaseModel):
    name: str
    relationship: str
    phone: str
    priority: int = 1


class ProfileMedicationRead(BaseModel):
    id: int
    name: str
    dose: str
    schedule_cron: str
    with_food: bool
    notes: str | None = None


class ProfileMedicationWrite(BaseModel):
    name: str
    dose: str
    schedule_cron: str
    with_food: bool = False
    notes: str | None = None


class PatientProfileRead(BaseModel):
    id: int
    name: str
    age: int
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    primary_language: str = "en"
    notes: str | None = None
    emergency_contacts: list[EmergencyContactRead] = Field(default_factory=list)
    medications: list[ProfileMedicationRead] = Field(default_factory=list)


class PatientProfileWrite(BaseModel):
    name: str
    age: int
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    primary_language: str = "en"
    notes: str | None = None
    emergency_contacts: list[EmergencyContactWrite] = Field(default_factory=list)
    medications: list[ProfileMedicationWrite] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Vitals ingestion (wearable -> backend) + read-back for the UI
# ---------------------------------------------------------------------------


class VitalReadingIngest(BaseModel):
    kind: str  # "hr" | "spo2" | "steps" | "calories" | ...
    value: float
    ts: datetime | None = None  # ISO-8601 UTC; defaults to server time if absent


class VitalIngestBatch(BaseModel):
    """Body of POST /vitals/ingest — a batch of offline-recorded readings."""

    patient_id: int = 1
    device: str = "galaxy_watch"  # stored as Vital.source
    readings: list[VitalReadingIngest] = Field(default_factory=list)


class VitalIngestResult(BaseModel):
    accepted: int


class VitalPoint(BaseModel):
    ts: str  # ISO-8601
    value: float
    systolic: float | None = None
    diastolic: float | None = None


class VitalSeries(BaseModel):
    kind: str
    points: list[VitalPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Lab / health records (document + parsed observation rows)
# ---------------------------------------------------------------------------


class LabObservationRead(BaseModel):
    id: int
    test_name: str
    value_text: str | None = None
    value_num: float | None = None
    unit: str | None = None
    reference_range: str | None = None
    flag: str | None = None
    category: str | None = None
    observed_at: datetime | None = None


class LabReportRead(BaseModel):
    id: int
    patient_id: int
    source: str
    lab_name: str | None = None
    ordering_provider: str | None = None
    collected_at: datetime | None = None
    reported_at: datetime | None = None
    document_filename: str | None = None
    status: str
    created_at: datetime
    observation_count: int = 0


class LabReportDetail(LabReportRead):
    raw_text: str | None = None
    observations: list[LabObservationRead] = Field(default_factory=list)


class LabUploadResult(BaseModel):
    report_id: int
    observations: int
    duplicate: bool = False
    status: str
