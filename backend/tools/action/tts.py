"""Text-to-speech tool.

Phase 0 (Windows): pyttsx3 — offline, uses Windows SAPI voices, no build deps.
Phase 7+: swap to Kokoro / NVIDIA Riva via Pipecat TTSService.

Note: pyttsx3 on Windows has a known bug where the SAPI5 event loop becomes
unreliable on the second+ call when a single engine instance is reused.
Reinitialising per call (~100 ms overhead) is the reliable workaround.
"""
from __future__ import annotations

import re

import pyttsx3
from loguru import logger

_VOICE_RATE = 165  # words per minute
_MARKDOWN_RE = re.compile(r"[*_`#\[\]>~]")  # strip common markdown symbols


def _clean(text: str) -> str:
    """Strip markdown characters that SAPI would read aloud literally."""
    return _MARKDOWN_RE.sub("", text).strip()


def speak(text: str, **_kwargs) -> None:
    """Convert text to speech and play it back synchronously."""
    clean = _clean(text)
    if not clean:
        return

    logger.debug("Speaking: {!r}", clean[:80])
    engine = pyttsx3.init()
    engine.setProperty("rate", _VOICE_RATE)
    engine.setProperty("volume", 1.0)

    # Use the first available female / Zira voice if present
    for v in engine.getProperty("voices"):
        if "female" in v.name.lower() or "zira" in v.id.lower():
            engine.setProperty("voice", v.id)
            break

    engine.say(clean)
    engine.runAndWait()
    engine.stop()
