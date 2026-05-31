"""Render a call announcement to a WAV file with Kokoro.

When the agent asks for a phone call, we synthesise the message the callee
should hear (with the same Kokoro voices used on the watch) and drop it as a
WAV under ``backend/static/audio/calls/`` — which is already served at
``/audio/calls/<id>.wav``. The Flutter app fetches and plays it once the call
connects.
"""
from __future__ import annotations

import pathlib
import uuid
import wave

from loguru import logger

from backend.voice import TTS_SAMPLE_RATE, synthesize_pcm, voice_for_route

_CALLS_DIR = pathlib.Path(__file__).resolve().parent.parent / "static" / "audio" / "calls"


def generate_call_wav(text: str, route: str = "safety") -> str:
    """Synthesise `text` to a WAV and return its public URL path.

    Returns ``/audio/calls/<id>.wav`` on success, or ``""`` if synthesis fails
    (the client can then fall back to its own on-device TTS).
    """
    if not text.strip():
        return ""
    try:
        pcm = b"".join(synthesize_pcm(text, voice_for_route(route)))
    except Exception as exc:  # noqa: BLE001 — never let TTS break a call
        logger.warning(f"[call-audio] synthesis failed: {exc}")
        return ""
    if not pcm:
        return ""

    _CALLS_DIR.mkdir(parents=True, exist_ok=True)
    call_id = uuid.uuid4().hex
    path = _CALLS_DIR / f"{call_id}.wav"
    try:
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(TTS_SAMPLE_RATE)  # 24 kHz
            wf.writeframes(pcm)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[call-audio] could not write WAV: {exc}")
        return ""
    return f"/audio/calls/{call_id}.wav"
