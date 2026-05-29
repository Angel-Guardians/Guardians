"""Risk Classifier - emits a CTAS-aligned SeverityTier for every event.

Hackathon v0: rule-based (keyword + duration + signal-source -> tier).
Phase 4 upgrade: Phi-3.5-mini fine-tuned on labelled events.

Runs in the Orchestrator BEFORE routing. Severity is a routing input,
not a sub-agent's job. See ARCHITECTURE.md sec. 3.5.
"""
from __future__ import annotations

from backend.db.models import SeverityTier
from backend.events.types import GuardianEvent


class RiskClassifier:
    async def classify(self, event: GuardianEvent) -> SeverityTier:
        """Return the severity tier for this event."""
        # TODO: rule table by event_type
        raise NotImplementedError
