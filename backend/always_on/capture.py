"""Always-on audio pipeline.

Phase 0: push-to-talk via Enter key. Press Enter to start, Enter again to stop.
         No wake word, no VAD — just mic → faster-whisper → text.

Phase 1+ will add openWakeWord + Silero VAD + continuous monitoring.
Runs CPU-only; the GPU is reserved for the LLM and TTS.
"""
from __future__ import annotations

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from loguru import logger

from backend.config import settings

SAMPLE_RATE = 16_000
CHANNELS = 1


class AudioPipeline:
    """Phase 0 audio pipeline: push-to-talk + faster-whisper transcription."""

    def __init__(self) -> None:
        logger.info("Loading Whisper model ({})…", settings.whisper_model)
        self._model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        self._frames: list[np.ndarray] = []
        self._recording = False
        self._stream: sd.InputStream | None = None
        logger.info("Whisper model ready.")

    # ------------------------------------------------------------------
    # Push-to-talk interface (Phase 0)
    # ------------------------------------------------------------------

    def start_recording(self) -> None:
        """Open the mic and begin buffering frames."""
        self._frames = []
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=self._audio_callback,
        )
        self._stream.start()
        logger.debug("Recording started.")

    def stop_and_transcribe(self) -> str:
        """Stop the mic, transcribe buffered audio, return text."""
        self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            return ""

        # Concatenate captured frames → 1-D float32 array at 16 kHz
        audio = np.concatenate(self._frames, axis=0).flatten()
        logger.debug("Transcribing {:.1f}s of audio…", len(audio) / SAMPLE_RATE)
        segments, _ = self._model.transcribe(audio, language="en", beam_size=5)
        text = " ".join(s.text.strip() for s in segments)
        logger.debug("Transcript: {!r}", text)
        return text

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,  # noqa: ARG002
        time: object,  # noqa: ARG002
        status: object,
    ) -> None:
        if status:
            logger.warning("Audio stream status: {}", status)
        if self._recording:
            self._frames.append(indata.copy())

    # ------------------------------------------------------------------
    # Phase 1+ continuous loop (not used in Phase 0)
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Continuous always-on loop (Phase 1+). Not used in Phase 0."""
        raise NotImplementedError("Phase 1+: wire openWakeWord + Silero VAD here.")
