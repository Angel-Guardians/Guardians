"""Event Pydantic models.

One model per event type. Every event carries an `id`, a `ts`, a `source`,
and a `payload`. Severity tags are added by the Risk Classifier on the
way through the Orchestrator.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from backend.db.models import SeverityTier


class GuardianEvent(BaseModel):
    """Base class for every event on the bus."""

    id: UUID = Field(default_factory=uuid4)
    ts: datetime = Field(default_factory=datetime.utcnow)
    source: str  # "always_on.wake", "agent.safety", "scheduler", ...
    severity: SeverityTier | None = None  # set by the Risk Classifier
    incident_id: int | None = None

    def to_log_payload(self) -> dict[str, Any]:
        """Strip transport fields; return what goes in the Event Log."""
        return self.model_dump(mode="json", exclude={"id", "ts", "source"})


# ---------------------------------------------------------------------------
# Always-on tier events
# ---------------------------------------------------------------------------


class WakeWordTriggeredEvent(GuardianEvent):
    type: Literal["wake_word_triggered"] = "wake_word_triggered"
    confidence: float


class PatientUtteranceEvent(GuardianEvent):
    type: Literal["patient_utterance"] = "patient_utterance"
    text: str
    duration_sec: float
    speaker_id: str | None = None  # if speaker recognition is on


class AudioEventDetectedEvent(GuardianEvent):
    type: Literal["audio_event_detected"] = "audio_event_detected"
    event_class: str  # "fall_sound" | "glass_break" | "cough_repeated" | "silence_unusual"
    confidence: float


class VitalSampleEvent(GuardianEvent):
    type: Literal["vital_sample"] = "vital_sample"
    kind: str  # "hr" | "spo2" | "bp_systolic" | "bp_diastolic" | "glucose"
    value: float
    device: str


class EnvSignalEvent(GuardianEvent):
    type: Literal["env_signal"] = "env_signal"
    signal: str  # "door_opened" | "smoke_alarm" | "kettle_on" | ...
    value: Any | None = None


# ---------------------------------------------------------------------------
# Reasoning / synthesized events (emitted by background workers)
# ---------------------------------------------------------------------------


class AnomalyDetectedEvent(GuardianEvent):
    type: Literal["anomaly_detected"] = "anomaly_detected"
    kind: str  # "hr_excursion" | "bp_trend" | "voice_stress" | ...
    z_score: float
    window_summary: dict[str, Any]


class PatternAbsenceEvent(GuardianEvent):
    type: Literal["pattern_absence"] = "pattern_absence"
    expected: str  # "morning_kettle" | "afternoon_walk" | ...
    minutes_overdue: int


# ---------------------------------------------------------------------------
# Scheduler events
# ---------------------------------------------------------------------------


class ScheduledReminderEvent(GuardianEvent):
    type: Literal["scheduled_reminder"] = "scheduled_reminder"
    medication_id: int
    medication_name: str
    scheduled_for: datetime


# ---------------------------------------------------------------------------
# UI / user-driven events
# ---------------------------------------------------------------------------


class TapConfirmedEvent(GuardianEvent):
    type: Literal["tap_confirmed"] = "tap_confirmed"
    confirms: str  # "reminder:<id>" | "checkin:<id>"


class UICommandEvent(GuardianEvent):
    type: Literal["ui_command"] = "ui_command"
    command: str
    args: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Routing / agent-internal events
# ---------------------------------------------------------------------------


class RoutingDecisionEvent(GuardianEvent):
    type: Literal["routing_decision"] = "routing_decision"
    routed_to: str  # sub-agent name
    matched_rule: str | None = None
    rationale: str | None = None


class ToolInvocationEvent(GuardianEvent):
    type: Literal["tool_invocation"] = "tool_invocation"
    tool: str
    args_summary: dict[str, Any]
    result_summary: dict[str, Any] | None = None


class HandoffEvent(GuardianEvent):
    """Cross-agent handoff. See ARCHITECTURE.md sec. 5 Flow 5."""

    type: Literal["handoff"] = "handoff"
    from_agent: str
    to_agent: str
    reason: str
    new_severity: SeverityTier | None = None
