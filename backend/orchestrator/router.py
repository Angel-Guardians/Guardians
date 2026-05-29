"""Hybrid router: rules first, LLM if ambiguous.

Rules table covers unambiguous signals (e.g. audio_event=fall_sound ->
Safety). Anything that falls through goes to Phi-3.5-mini for a
classification.
"""
from __future__ import annotations

from backend.events.types import GuardianEvent


# Static routing rules. Order matters; first match wins.
RULES: list[tuple[str, str, str]] = [
    # (event_type, condition_summary, target_agent)
    ("audio_event_detected", "fall_sound|glass_break", "safety"),
    ("vital_sample", "any", "health"),
    ("scheduled_reminder", "any", "reminder"),
    ("tap_confirmed", "any", "reminder"),
    ("anomaly_detected", "any", "health"),
    ("pattern_absence", "any", "safety"),
    # Patient utterances fall through to LLM routing
]


class Router:
    """Decides which sub-agent owns an event."""

    def __init__(self, llm_router: object | None = None) -> None:
        self.llm_router = llm_router  # an LLM-backed classifier; nullable for tests

    async def route(self, event: GuardianEvent) -> str:
        """Return the name of the sub-agent that should handle this event."""
        # TODO: walk RULES; if no match, fall through to llm_router.classify(event)
        raise NotImplementedError
