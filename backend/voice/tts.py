"""Text-to-speech for the voice WebSocket.

Streams the spoken reply back to the watch as raw 16-bit mono PCM at 24 kHz, which
drops straight onto the watch's AudioTrack with no decoding. Synthesis is a blocking
generator so the endpoint can forward each chunk the instant it arrives (first audio
out well before the whole sentence is rendered).

Two backends behind one `(text, voice) -> Iterator[bytes]` contract:

  * **kokoro** (default) — local, offline neural TTS (backend/voice/kokoro_tts.py).
  * **openai** — cloud `gpt-4o-mini-tts`; needs OPENAI_API_KEY.

`settings.tts_backend` selects: "kokoro", "openai", or "auto" (kokoro if importable,
else openai). When Kokoro is selected but can't load (package/model missing), we fall
back to OpenAI automatically — but only before any audio has been emitted, so a turn
never double-speaks.
"""
from __future__ import annotations

from collections.abc import Iterator

from loguru import logger

from backend.config import settings

# Both backends emit 24 kHz, 16-bit, mono, little-endian PCM.
TTS_SAMPLE_RATE = 24_000

# OpenAI voice per specialist (used when the OpenAI backend is active).
_VOICE_BY_ROUTE: dict[str, str] = {
    "safety": "onyx",      # urgent, grounded
    "health": "nova",      # calm, clear
    "companion": "shimmer",  # warm
    "reminder": "alloy",   # gentle, neutral
    "behavior": "echo",    # level, de-escalating
    "caregiver": "fable",  # formal
}
_DEFAULT_VOICE = "alloy"
_OPENAI_VOICES = {"alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"}


def _kokoro_importable() -> bool:
    import importlib.util

    return importlib.util.find_spec("kokoro") is not None


def _use_kokoro() -> bool:
    """Whether the active config wants the Kokoro backend."""
    backend = (settings.tts_backend or "kokoro").strip().lower()
    if backend == "openai":
        return False
    if backend == "kokoro":
        return True
    return _kokoro_importable()  # "auto"


def voice_for_route(route: str | None) -> str:
    """Pick the voice for the specialist that handled the turn (backend-aware)."""
    if _use_kokoro():
        from backend.voice.kokoro_tts import kokoro_voice_for_route

        return kokoro_voice_for_route(route)
    return _VOICE_BY_ROUTE.get(route or "", settings.tts_voice or _DEFAULT_VOICE)


def _synthesize_pcm_openai(text: str, voice: str | None) -> Iterator[bytes]:
    """Yield 24 kHz 16-bit mono PCM via OpenAI streaming TTS."""
    from backend.voice.openai_creds import openai_api_key

    key = openai_api_key()
    if not key:
        raise RuntimeError("No text-to-speech backend available: set OPENAI_API_KEY.")

    # A Kokoro voice id (e.g. "af_heart") won't be valid here on fallback — sanitise.
    if voice not in _OPENAI_VOICES:
        voice = settings.tts_voice if settings.tts_voice in _OPENAI_VOICES else _DEFAULT_VOICE

    from openai import OpenAI

    client = OpenAI(api_key=key)
    with client.audio.speech.with_streaming_response.create(
        model=settings.tts_model,
        voice=voice,
        input=text,
        response_format="pcm",
    ) as response:
        # ~20 ms of audio per 1 KB; 4 KB keeps frames small without flooding the bus.
        yield from response.iter_bytes(chunk_size=4096)


def synthesize_pcm(text: str, voice: str | None = None) -> Iterator[bytes]:
    """Yield 24 kHz 16-bit mono PCM chunks for `text`. Blocking generator.

    Uses the configured backend (Kokoro by default), falling back to OpenAI if
    Kokoro is selected but cannot render. Raises RuntimeError only if no backend
    can produce audio (e.g. OpenAI fallback with no key).
    """
    if not text.strip():
        return

    if _use_kokoro():
        gen = None
        first: bytes | None = None
        try:
            from backend.voice.kokoro_tts import synthesize_pcm_kokoro

            gen = synthesize_pcm_kokoro(text, voice)
            # Pull the first frame here so model-load / import failures surface
            # *before* we've emitted anything and can cleanly fall back.
            first = next(gen, None)
        except Exception as exc:  # noqa: BLE001 - fall back to OpenAI
            logger.warning(f"[tts] Kokoro unavailable ({exc}); falling back to OpenAI.")
            gen = None

        if gen is not None:
            if first is not None:
                yield first
                yield from gen
            return

    yield from _synthesize_pcm_openai(text, voice)
