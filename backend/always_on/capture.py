"""Always-on audio pipeline.

  mic -> openWakeWord -> Silero VAD -> faster-whisper-int8 -> text

On wake-word trigger: open a VAD-bounded utterance, transcribe, emit a
PatientUtteranceEvent. Total target latency under 1.5s from end of
speech to event on the bus.

Runs as a coroutine inside the always-on process. CPU-only; the GPU is
reserved for the LLM and TTS in the on-demand process.
"""
from __future__ import annotations


class AudioPipeline:
    """Single audio pipeline. One instance per process."""

    def __init__(self) -> None:
        # TODO: load openWakeWord, Silero VAD, faster-whisper model
        ...

    async def run(self) -> None:
        """Capture audio frames forever; emit events on wake + utterance."""
        # TODO: sounddevice ring buffer -> wake -> vad -> stt -> emit
        raise NotImplementedError
