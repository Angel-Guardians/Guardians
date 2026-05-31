"""Shared building blocks for agent system prompts.

The single source of truth for patient/persona context. Every agent prompt
composes this in via `with_context(...)`, so the person's details (name, meds,
emergency contact, history) live in ONE place — never duplicated across six files.

Two demo personas are defined below. Which one is live is chosen at process
start by the `GUARDIAN_PERSONA` environment variable:

    GUARDIAN_PERSONA=matthew   (default — Scenario 1, the night-fall demo)
    GUARDIAN_PERSONA=sarah     (Scenario 2, the proactive-companion demo)

Switching scenarios between takes is therefore an env change + restart, with no
code edit on camera. Because prompts are composed at import time, the persona is
fixed for the lifetime of the process (restart to switch).
"""
from __future__ import annotations

import os

# --- Demo personas --------------------------------------------------------
# Each block is self-describing: it names the person and their emergency
# contact so the specialist prompts never need a hardcoded name.

_MATTHEW = """\
Person on file: Matthew, 78, lives alone. Cardiac history: atrial fibrillation,
prior heart attack with stents, mild heart failure; on a blood thinner (apixaban).
Primary emergency contact: Sophie (a nurse in the same building, CPR/AED-trained).
Daughter Claire (in Ottawa) is notified after Sophie.
Medications: apixaban (blood thinner), plus his cardiac regimen."""

_SARAH = """\
Person on file: Sarah, 35, lives alone, wheelchair user (T10 paraplegia).
History of moderate depression; enjoys watercolour painting and knitting.
Primary emergency contact: her sister Amara.
Medications: sertraline 50 mg (morning, with breakfast)."""

_PERSONAS = {"matthew": _MATTHEW, "sarah": _SARAH}

# The active persona context, selected by env var (default: matthew).
_ACTIVE_PERSONA = os.environ.get("GUARDIAN_PERSONA", "matthew").strip().lower()
PATIENT_CONTEXT = _PERSONAS.get(_ACTIVE_PERSONA, _MATTHEW)


def with_context(body: str) -> str:
    """Append the shared patient context to an agent-specific prompt body."""
    return f"{body.rstrip()}\n\n{PATIENT_CONTEXT}\n"
