"""Per-sub-agent voice profiles.

Each sub-agent has a distinct tone. The Notification Dispatcher and TTS
tool read the profile and map it to a Kokoro voice ID + speech rate +
pitch adjustments.
"""
from __future__ import annotations

from enum import Enum


class VoiceProfile(str, Enum):
    URGENT = "urgent"           # Safety - sharp, short, loud
    CALM = "calm"               # Health, Companion - measured, reassuring
    GENTLE = "gentle"           # Reminder - warm, soft
    FIRM = "firm"               # Behavior - de-escalating, level
    FORMAL = "formal"           # Caregiver Liaison - clinical when needed
    CLONED = "cloned_family"    # PTSD/wandering/sundowning - per-patient


# Kokoro voice IDs per profile. TODO: fill in real voice IDs after auditioning.
KOKORO_VOICE_BY_PROFILE: dict[VoiceProfile, str] = {
    VoiceProfile.URGENT: "af_bella",
    VoiceProfile.CALM: "af_nicole",
    VoiceProfile.GENTLE: "af_sky",
    VoiceProfile.FIRM: "am_michael",
    VoiceProfile.FORMAL: "am_adam",
    VoiceProfile.CLONED: "custom",  # resolved per-patient at runtime
}
