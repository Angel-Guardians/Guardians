"""Risk Classifier - emits a CTAS-aligned SeverityTier for every event.

Hackathon v0: rule-based (keyword + duration + signal-source -> tier).
Phase 4 upgrade: Phi-3.5-mini fine-tuned on labelled events.

Runs in the Orchestrator BEFORE routing. Severity is a routing input,
not a sub-agent's job. See ARCHITECTURE.md sec. 3.5.
"""
from __future__ import annotations

from backend.db.models import SeverityTier
from backend.events.types import AudioEventDetectedEvent, GuardianEvent, VitalSampleEvent


class RiskClassifier:
    async def classify(self, event: GuardianEvent) -> SeverityTier:
        """Return the severity tier for this event."""
        if isinstance(event, AudioEventDetectedEvent) and event.event_class in (
            "fall_sound",
            "glass_break",
        ):
            return SeverityTier.CALL

        if isinstance(event, VitalSampleEvent) and event.kind in (
            "fall_suspected",
            "fall_confirmed",
        ):
            return SeverityTier.CALL

        event_type = getattr(event, "type", None)
        if event_type == "audio_event_detected":
            payload = event.model_dump()
            if payload.get("event_class") in ("fall_sound", "glass_break"):
                return SeverityTier.CALL
        if event_type == "vital_sample":
            payload = event.model_dump()
            if payload.get("kind") in ("fall_suspected", "fall_confirmed"):
                return SeverityTier.CALL

        return SeverityTier.WHISPER
