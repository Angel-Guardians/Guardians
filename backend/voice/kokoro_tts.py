"""Kokoro text-to-speech backend.

Local, offline neural TTS via the `kokoro` package (hexgrad/Kokoro-82M). Renders
24 kHz float32 audio natively, which we convert to 16-bit mono little-endian PCM —
the exact format the watch's AudioTrack expects — and yield in small frames so the
voice WebSocket can forward first audio with low latency.

Same `(text, voice) -> Iterator[bytes]` contract as the OpenAI path in tts.py, so
the endpoint and the watch are unchanged regardless of which backend renders.

The `kokoro` package is an optional dependency (``pip install -e ".[audio]"``); the
caller (tts.py) falls back to OpenAI if it (or its model) can't be loaded.
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
from loguru import logger

from backend.config import settings

# Kokoro renders at 24 kHz — matches TTS_SAMPLE_RATE so no resampling is needed.
KOKORO_SAMPLE_RATE = 24_000

# Forward each ~4 KB of PCM (~85 ms) so the watch starts speaking quickly.
_FRAME_BYTES = 4096

# Map each Guardian specialist to a Kokoro voice that fits its tone. Mirrors the
# VoiceProfile intent in backend/agents/voice_profiles.py.
_KOKORO_VOICE_BY_ROUTE: dict[str, str] = {
    "safety": "af_bella",     # urgent, grounded
    "health": "af_nicole",    # calm, clear
    "companion": "af_heart",  # warm
    "reminder": "af_sky",     # gentle
    "behavior": "am_michael",  # level, de-escalating
    "caregiver": "am_adam",   # formal
}

# Lazily-built, reused across turns — model load is expensive (~1 s + a one-time
# weight download on first ever use).
_pipeline = None


def kokoro_voice_for_route(route: str | None) -> str:
    """Pick the Kokoro voice for the specialist that handled the turn."""
    return _KOKORO_VOICE_BY_ROUTE.get(route or "", settings.kokoro_voice_default)


def _get_pipeline():
    """Build (once) and return the Kokoro pipeline. Raises if kokoro isn't usable."""
    global _pipeline
    if _pipeline is None:
        from kokoro import KPipeline  # optional dep; ImportError → caller falls back

        logger.info(f"[kokoro] loading pipeline (lang_code={settings.kokoro_lang_code})")
        _pipeline = KPipeline(lang_code=settings.kokoro_lang_code)
    return _pipeline


def _audio_of(item) -> object | None:
    """Pull the audio array out of a Kokoro result (tuple or Result object)."""
    audio = getattr(item, "audio", None)
    if audio is None and isinstance(item, (tuple, list)) and item:
        audio = item[-1]
    return audio


def _to_pcm16(audio) -> bytes:
    """Convert a float32 [-1, 1] waveform (numpy/torch) to 16-bit LE PCM bytes."""
    if hasattr(audio, "detach"):  # torch.Tensor
        audio = audio.detach().cpu().numpy()
    samples = np.asarray(audio, dtype=np.float32)
    samples = np.clip(samples, -1.0, 1.0)
    return (samples * 32767.0).astype("<i2").tobytes()


def synthesize_pcm_kokoro(text: str, voice: str | None = None) -> Iterator[bytes]:
    """Yield 24 kHz 16-bit mono PCM frames for `text` using Kokoro. Blocking generator."""
    if not text.strip():
        return

    pipeline = _get_pipeline()
    chosen = voice or settings.kokoro_voice_default

    for item in pipeline(text, voice=chosen, speed=settings.kokoro_speed):
        audio = _audio_of(item)
        if audio is None:
            continue
        pcm = _to_pcm16(audio)
        # Re-chunk each rendered segment into small frames for smooth streaming.
        for start in range(0, len(pcm), _FRAME_BYTES):
            yield pcm[start : start + _FRAME_BYTES]
