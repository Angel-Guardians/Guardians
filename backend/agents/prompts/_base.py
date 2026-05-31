"""Shared building blocks for agent system prompts.

The single source of truth for patient/persona context. Every agent prompt
composes this in via `with_context(...)`. At runtime, GuardianAgent loads the
active patient from the DB and calls `build_patient_context` to produce the
context block, which is then injected as a system message per turn.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.api.schemas import PatientProfileRead


def build_patient_context(profile: "PatientProfileRead") -> str:
    """Build a patient context block from a live profile."""
    lines = [
        f"Patient on file: {profile.name}, {profile.age} years old.",
    ]
    if profile.location:
        lines.append(f"Home address: {profile.location}.")
    if profile.bio:
        lines.append(f"About {profile.name}: {profile.bio}")
    if profile.conditions:
        lines.append(f"Conditions: {', '.join(profile.conditions)}.")
    if profile.allergies:
        lines.append(f"Allergies: {', '.join(profile.allergies)}.")
    if profile.medications:
        med_strs = [f"{m.name} {m.dose}" for m in profile.medications]
        lines.append(f"Medications: {', '.join(med_strs)}.")
    if profile.emergency_contacts:
        contacts = [
            f"{c.name} ({c.relationship}, {c.phone})"
            for c in sorted(profile.emergency_contacts, key=lambda c: c.priority)
        ]
        lines.append(f"Emergency contacts: {', '.join(contacts)}.")
    if profile.notes:
        lines.append(f"Notes: {profile.notes}")
    return "\n".join(lines)


def with_context(body: str) -> str:
    """Return the prompt body as-is; patient context is injected at runtime."""
    return body.rstrip() + "\n"
