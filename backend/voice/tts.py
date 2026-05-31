"""Text-to-speech for the voice WebSocket.

Streams the spoken reply back to the watch as raw 16-bit mono PCM at 24 kHz —
OpenAI's `pcm` format is exactly that, so it drops straight onto the watch's
AudioTrack with no decoding. Synthesis is a blocking generator so the endpoint
can forward each chunk the instant it arrives (first audio out well before the
whole sentence is rendered).

This is the on-demand counterpart to the Kokoro path sketched in
backend/agents/voice_profiles.py; swapping in Kokoro later means replacing the
body of `synthesize_pcm` and keeping the same `(text, voice) -> Iterator[bytes]`
shape and 24 kHz output.
"""
from __future__ import annotations

from collections.abc import Iterator

from backend.config import settings

# OpenAI's `response_format="pcm"` emits 24 kHz, 16-bit, mono, little-endian.
TTS_SAMPLE_RATE = 24_000

# Map each Guardian specialist to an OpenAI voice that fits its tone (mirrors the
# VoiceProfile intent in backend/agents/voice_profiles.py).
_VOICE_BY_ROUTE: dict[str, str] = {
    "safety": "onyx",      # urgent, grounded
    "health": "nova",      # calm, clear
    "companion": "shimmer",  # warm
    "reminder": "alloy",   # gentle, neutral
    "behavior": "echo",    # level, de-escalating
    "caregiver": "fable",  # formal
}
_DEFAULT_VOICE = "alloy"


def voice_for_route(route: str | None) -> str:
    """Pick the OpenAI voice for the specialist that handled the turn."""
    return _VOICE_BY_ROUTE.get(route or "", settings.tts_voice or _DEFAULT_VOICE)


def synthesize_pcm(text: str, voice: str | None = None) -> Iterator[bytes]:
    """Yield 24 kHz 16-bit mono PCM chunks for `text`. Blocking generator.

    Raises RuntimeError if no TTS backend is configured (no OPENAI_API_KEY).
    """
    if not text.strip():
        return
    if not settings.openai_api_key:
        raise RuntimeError("No text-to-speech backend available: set OPENAI_API_KEY.")

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    with client.audio.speech.with_streaming_response.create(
        model=settings.tts_model,
        voice=voice or settings.tts_voice or _DEFAULT_VOICE,
        input=text,
        response_format="pcm",
    ) as response:
        # ~20 ms of audio per 1 KB; 4 KB keeps frames small without flooding the bus.
        yield from response.iter_bytes(chunk_size=4096)
