"""Shared building blocks for agent system prompts.

The single source of truth for patient/persona context. Every agent prompt
composes this in via `with_context(...)`, so a change to Eleanor's details
(meds, emergency contact, history) happens here ONCE — never in six places.
"""
from __future__ import annotations

# --- Shared persona block -------------------------------------------------
# Edit Eleanor's details here and every agent picks them up automatically.
PATIENT_CONTEXT = """\
Patient on file: Eleanor, 70 years old, lives alone. Known cardiac history.
Emergency contact: Maria (daughter, +1-416-555-0192).
Medications: metoprolol 50 mg (morning), aspirin 81 mg (morning)."""


def with_context(body: str) -> str:
    """Append the shared patient context to an agent-specific prompt body."""
    return f"{body.rstrip()}\n\n{PATIENT_CONTEXT}\n"
