"""Speech-to-text for the voice WebSocket.

Input is always raw 16-bit mono PCM (what the watch's AudioRecord produces). Two
backends, tried in order:

  1. faster-whisper, if installed — fully local/offline, matches the always-on
     design (backend/always_on/capture.py). Model is loaded once and reused.
  2. OpenAI Whisper (`whisper-1`) — needs OPENAI_API_KEY but no local model. The
     PCM is wrapped in a WAV container in memory and posted.

Whichever is available wins; if neither is, we raise so the endpoint can surface
a clear error to the watch rather than silently returning "".
"""
from __future__ import annotations

import io
import wave

from loguru import logger

from backend.config import settings

# Lazily-initialised faster-whisper model (loading it is expensive).
_whisper_model = None
_whisper_unavailable = False


def _pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    """Wrap raw 16-bit mono PCM in a minimal WAV container (for OpenAI upload)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buf.getvalue()


def _try_faster_whisper(pcm: bytes, sample_rate: int) -> str | None:
    """Transcribe with a local faster-whisper model, or None if unavailable."""
    global _whisper_model, _whisper_unavailable
    if _whisper_unavailable:
        return None
    try:
        import numpy as np

        if _whisper_model is None:
            from faster_whisper import WhisperModel

            logger.info(f"Loading faster-whisper model '{settings.whisper_model}' ...")
            _whisper_model = WhisperModel(
                settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
    except Exception as exc:  # noqa: BLE001 — import or model-load failure
        logger.info(f"faster-whisper unavailable ({exc}); will try OpenAI STT.")
        _whisper_unavailable = True
        return None

    # int16 PCM -> float32 in [-1, 1], which faster-whisper expects. It resamples
    # to 16 kHz internally, but we already capture at 16 kHz so this is a no-op.
    audio = np.frombuffer(pcm, dtype=np.int16).astype("float32") / 32768.0
    segments, _ = _whisper_model.transcribe(audio, language="en", vad_filter=True)
    return "".join(seg.text for seg in segments).strip()


def _try_openai(pcm: bytes, sample_rate: int) -> str | None:
    """Transcribe via OpenAI Whisper, or None if no key is configured."""
    if not settings.openai_api_key:
        return None
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    wav = _pcm_to_wav(pcm, sample_rate)
    # The SDK keys off the filename's extension to set the content type.
    file_tuple = ("utterance.wav", wav, "audio/wav")
    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=file_tuple,
        language="en",
    )
    return (result.text or "").strip()


def transcribe_pcm(pcm: bytes, sample_rate: int = 16_000) -> str:
    """Transcribe raw 16-bit mono PCM to text. Blocking — call via to_thread.

    Returns the transcript (possibly empty if the utterance was silence). Raises
    RuntimeError only if no STT backend is configured at all.
    """
    if not pcm:
        return ""

    text = _try_faster_whisper(pcm, sample_rate)
    if text is not None:
        return text

    text = _try_openai(pcm, sample_rate)
    if text is not None:
        return text

    raise RuntimeError(
        "No speech-to-text backend available: install faster-whisper "
        "(pip install '.[audio]') or set OPENAI_API_KEY."
    )
