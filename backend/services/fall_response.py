"""Automatic Safety-agent response when a fall is ingested."""
from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from loguru import logger

from backend.api.call_bridge import emit_call_requests
from backend.api.turn import _event_for
from backend.events.types import TranscriptEvent
from backend.voice.dashboard import speak_reply

if TYPE_CHECKING:
    from backend.agents.guardian import GuardianAgent
    from backend.events.bus import EventBus
    from backend.voice.monitor import VoiceMonitor

_COOLDOWN_SEC = 60.0
_last_fired: dict[tuple[int, str], float] = {}


def _fall_alert_message(kind: str, peak_g: float) -> str:
    severity = "confirmed" if kind == "fall_confirmed" else "possible"
    return (
        f"[AUTOMATED ALERT] The wearable detected a {severity} fall "
        f"(peak {peak_g:.1f}g). The patient may have fallen and cannot get up. "
        "Speak to them calmly: ask if they are hurt and whether they need help. "
        "Follow safety protocol."
    )


def should_trigger(patient_id: int, kind: str) -> bool:
    """Debounce repeated fall readings from batch sync."""
    if kind not in ("fall_suspected", "fall_confirmed"):
        return False
    key = (patient_id, kind)
    now = time.monotonic()
    last = _last_fired.get(key, 0.0)
    if now - last < _COOLDOWN_SEC:
        return False
    _last_fired[key] = now
    return True


async def trigger_fall_response(
    guardian: GuardianAgent | None,
    bus: EventBus | None,
    patient_id: int,
    kind: str,
    peak_g: float,
    monitor: VoiceMonitor | None = None,
) -> None:
    """Run a Safety turn and publish pipeline events to the bus."""
    if guardian is None:
        logger.warning("Fall detected but GuardianAgent is not initialised.")
        return
    if bus is None:
        return

    message = _fall_alert_message(kind, peak_g)
    loop = asyncio.get_running_loop()

    def emit(kind_str: str, payload: dict) -> None:
        event = _event_for(kind_str, payload)
        if event is not None:
            asyncio.run_coroutine_threadsafe(bus.publish(event), loop)

    await bus.publish(TranscriptEvent(source="api.fall_alert", text=message))

    try:
        result = await asyncio.to_thread(guardian.turn, message, emit, patient_id)
        await emit_call_requests(bus, result, patient_id)
        # Voice the safety reply through Kokoro to the Live page speaker.
        await speak_reply(monitor, result.get("reply", ""), result.get("route", "safety"))
        logger.info(
            f"Fall response complete for patient #{patient_id}: route={result.get('route')}",
        )
    except Exception:
        logger.exception(f"Fall response failed for patient #{patient_id}")
