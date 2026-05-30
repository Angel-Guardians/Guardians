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
# Reminder intake log (medication adherence)
# ---------------------------------------------------------------------------


class ReminderIntake(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    medication_id: int = Field(foreign_key="medication.id")
    scheduled_for: datetime
    confirmed_at: datetime | None = None
    method: str | None = None  # "tap", "voice", "auto"
