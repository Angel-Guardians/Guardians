"""Speak an agent reply to dashboard listeners (the Live page speaker) via Kokoro.

This mirrors the watch-mic fan-out in ``backend/api/voice.py``: it emits the same
control events the dashboard's ``/voice/listen`` client already understands
(``mic_begin`` -> ``reply`` -> ``mic_end``) and streams 24 kHz PCM in between. So a
reply produced by a *typed* turn or by the *automatic* fall response is heard in the
browser exactly like a spoken watch turn — using the real TTS engine (Kokoro
offline, OpenAI cloud as fallback), not a browser voice.

Only the patient's lines are ever scripted in the demo; everything Guardian says
here is the live LLM reply rendered through the production voice stack.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from backend.voice import TTS_SAMPLE_RATE, synthesize_pcm, voice_for_route

if TYPE_CHECKING:
    from backend.voice.monitor import VoiceMonitor


async def speak_reply(monitor: VoiceMonitor | None, text: str, route: str = "companion") -> None:
    """Render `text` with the route's voice and fan the audio out to dashboards.

    No-op when there's no monitor or nothing to say. The control events are always
    broadcast (so the speaker card shows what Guardian said); the PCM is only
    rendered when a dashboard is actually listening, so we never burn TTS cycles
    for nobody.
    """
    if monitor is None or not (text and text.strip()):
        return

    monitor.broadcast_event({"type": "mic_begin", "sample_rate": TTS_SAMPLE_RATE})
    monitor.broadcast_event({"type": "reply", "text": text, "route": route})

    if monitor.has_listeners:
        loop = asyncio.get_running_loop()
        voice = voice_for_route(route)

        def produce() -> None:
            for chunk in synthesize_pcm(text, voice):
                loop.call_soon_threadsafe(monitor.broadcast_audio, chunk)

        try:
            await loop.run_in_executor(None, produce)
        except Exception:  # noqa: BLE001 — a TTS hiccup must not break the turn
            logger.exception("dashboard TTS failed")

    monitor.broadcast_event({"type": "mic_end"})
