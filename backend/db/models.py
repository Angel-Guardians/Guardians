"""SQLModel data models.

The Event Log is the source of truth. Every other table is either a
projection of it or a slow-moving record (Patient, Medication, Reminder,
ConsentMatrix).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlmodel import Column, Field, JSON, SQLModel


class SeverityTier(str, Enum):
    """CTAS-aligned severity. See ARCHITECTURE.md sec. 3.5."""

    WHISPER = "tier_1_whisper"
    NUDGE = "tier_2_nudge"
    ALARM = "tier_3_alarm"
    CALL = "tier_4_call"


class IncidentStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# ---------------------------------------------------------------------------
# Patient profile + consent
# ---------------------------------------------------------------------------


class Patient(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    age: int
    conditions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    allergies: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    primary_language: str = "en"
    notes: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmergencyContact(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    name: str
    relationship: str  # "daughter", "neighbour", "family_doctor", etc.
    phone: str
    priority: int = 1  # 1 = call first


class Medication(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    name: str
    dose: str
    schedule_cron: str  # APScheduler-compatible cron
    with_food: bool = False
    notes: str | None = None


class ConsentMatrix(SQLModel, table=True):
    """Per-recipient, per-data-category consent. See ARCHITECTURE.md sec. 3.6."""

    id: int | None = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    recipient: str  # "family", "family_doctor", "counselor", "probation_officer", ...
    data_category: str  # "vitals", "voice_transcript", "voice_features_only", ...
    mode: str  # "always" | "on_incident" | "on_explicit_ask" | "never"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Event Log - THE source of truth (ARCHITECTURE.md sec. 3.3)
# ---------------------------------------------------------------------------


class EventLogEntry(SQLModel, table=True):
    """Append-only. Add @hash_chain in Phase 7 for tamper evidence."""

    id: int | None = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    source: str  # "always_on.audio", "agent.safety", "tool.call_911", ...
    event_type: str  # matches one of backend.events.types
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    severity: SeverityTier | None = None
    incident_id: int | None = Field(default=None, foreign_key="incident.id")
    reason: str | None = None  # routing decision rationale


# ---------------------------------------------------------------------------
# Incident - a coherent active episode (a fall, a panic attack, a wandering)
# ---------------------------------------------------------------------------


class Incident(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: datetime | None = None
    status: IncidentStatus = IncidentStatus.OPEN
    initial_severity: SeverityTier
    peak_severity: SeverityTier
    primary_agent: str  # which sub-agent owned this
    summary: str | None = None  # generated at close


# ---------------------------------------------------------------------------
# Vitals - relational fallback for dev/queries; InfluxDB is the prod time-series store
# ---------------------------------------------------------------------------


class Vital(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    ts: datetime = Field(default_factory=datetime.utcnow)
    kind: str  # "hr", "spo2", "bp_systolic", "bp_diastolic", "glucose"
    value: float
    source: str  # "polar_h10", "omron_bp", "dexcom_g7", "manual"


# ---------------------------------------------------------------------------
# Location - GPS position track from the wearable (every ~5 min)
# ---------------------------------------------------------------------------


class Location(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    ts: datetime = Field(default_factory=datetime.utcnow)
    lat: float
    lng: float
    accuracy: float | None = None  # metres
    source: str  # "galaxy_watch"


# ---------------------------------------------------------------------------
# Reminder intake log (medication adherence)
# ---------------------------------------------------------------------------


class ReminderIntake(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    medication_id: int = Field(foreign_key="medication.id")
    scheduled_for: datetime
    confirmed_at: datetime | None = None
    method: str | None = None  # "tap", "voice", "auto"


# ---------------------------------------------------------------------------
# Lab / health records - a results document ("doc") + its parsed rows
# ---------------------------------------------------------------------------


class LabReport(SQLModel, table=True):
    """A single lab-results document (e.g. a LifeLabs PDF) and its metadata.

    The original file lives on disk (``document_path`` under
    ``settings.lab_documents_dir``); the parsed analytes are ``LabObservation``
    rows linked back here. ``document_sha256`` makes ingestion idempotent.
    """

    id: int | None = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    source: str  # "lifelabs_upload" | "lifelabs_mycarecompass" | "manual"
    external_id: str | None = Field(default=None, index=True)  # portal/report id
    lab_name: str | None = None  # "LifeLabs"
    ordering_provider: str | None = None
    collected_at: datetime | None = None
    reported_at: datetime | None = None
    document_path: str | None = None  # relative to settings.lab_documents_dir
    document_filename: str | None = None
    document_sha256: str | None = Field(default=None, index=True)
    content_type: str | None = None
    raw_text: str | None = None  # full extracted text (search / LLM fallback)
    status: str = "parsed"  # "parsed" | "needs_review" | "raw_only"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LabObservation(SQLModel, table=True):
    """One analyte/result line within a ``LabReport`` (a 'related row')."""

    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="labreport.id")
    patient_id: int = Field(foreign_key="patient.id")
    test_name: str  # "Hemoglobin", "Glucose, Fasting"
    value_text: str | None = None  # value as printed ("118", "Negative")
    value_num: float | None = None  # parsed numeric value when possible
    unit: str | None = None  # "g/L", "mmol/L"
    reference_range: str | None = None  # "120 - 160"
    flag: str | None = None  # "H" | "L" | "A" | "C" | None (normal)
    category: str | None = None  # section, e.g. "Hematology"
    observed_at: datetime | None = None
    loinc_code: str | None = None  # optional standard code (future)
