"""Bidirectional voice WebSocket.

  ws://<host>/voice/ws

One socket carries a full spoken turn in both directions. The watch streams
microphone PCM up; the backend transcribes it, runs one Guardian turn, and
streams the synthesised reply PCM back down the same socket. Each turn is also
mirrored onto the EventBus (TranscriptEvent + AgentReplyEvent) so the Live
dashboard animates voice turns exactly like typed ones (see api/turn.py).

Wire protocol — control is JSON **text** frames, audio is **binary** frames:

  watch -> backend
    {"type":"start","patient_id":1,"sample_rate":16000}
    <binary PCM frames: 16-bit mono LE, sample_rate Hz>   (repeated)
    {"type":"end"}

  backend -> watch
    {"type":"transcript","text":"..."}            # what we heard
    {"type":"reply","text":"...","route":"..."}   # what the agent said
    {"type":"tts_begin","sample_rate":24000}
    <binary PCM frames: 16-bit mono LE, 24 kHz>           (streamed as rendered)
    {"type":"tts_end"}
    {"type":"error","message":"..."}              # on any failure; turn aborts

The watch is deliberately dumb: it just records-and-streams between push-to-talk
press/release. VAD, STT, the LLM, and TTS all live here, so the device stays
battery-cheap and the heavy models stay server-side.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from backend.events.types import AgentReplyEvent, TranscriptEvent
from backend.voice import TTS_SAMPLE_RATE, synthesize_pcm, transcribe_pcm, voice_for_route

router = APIRouter()

# Refuse pathologically long uploads (a stuck mic). 16 kHz * 2 bytes * 60 s.
_MAX_UTTERANCE_BYTES = 16_000 * 2 * 60


async def _stream_tts(websocket: WebSocket, text: str, voice: str) -> None:
    """Render `text` and forward each PCM chunk as it arrives.

    synthesize_pcm is a blocking generator, so it runs in a thread and hands
    chunks back to the event loop through a queue — keeping first-audio latency low
    without blocking the socket.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=64)

    def produce() -> None:
        try:
            for chunk in synthesize_pcm(text, voice):
                asyncio.run_coroutine_threadsafe(queue.put(chunk), loop).result()
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    producer = loop.run_in_executor(None, produce)
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        await websocket.send_bytes(chunk)
    await producer  # surface any exception raised inside the generator


async def _handle_utterance(websocket: WebSocket, pcm: bytes, sample_rate: int, ctx) -> None:
    """Transcribe one utterance, run a turn, and speak the reply back."""
    guardian = ctx.guardian
    bus = ctx.bus
    if guardian is None:
        await websocket.send_json({"type": "error", "message": "Agent not configured."})
        return

    # 1) Speech -> text (blocking model work off the loop).
    text = (await asyncio.to_thread(transcribe_pcm, pcm, sample_rate)).strip()
    await websocket.send_json({"type": "transcript", "text": text})
    if not text:
        return  # silence / no speech detected; nothing to answer
    if bus is not None:
        await bus.publish(TranscriptEvent(source="voice.ws", text=text))

    # 2) One Guardian turn (synchronous graph -> worker thread).
    result = await asyncio.to_thread(guardian.turn, text)
    reply = result.get("reply", "")
    route = result.get("route", "companion")
    await websocket.send_json({"type": "reply", "text": reply, "route": route})
    if bus is not None:
        await bus.publish(AgentReplyEvent(source=f"agent.{route}", agent=route, text=reply))

    # 3) Text -> speech, streamed back as it renders.
    if reply.strip():
        await websocket.send_json({"type": "tts_begin", "sample_rate": TTS_SAMPLE_RATE})
        await _stream_tts(websocket, reply, voice_for_route(route))
        await websocket.send_json({"type": "tts_end"})


class _Ctx:
    """Per-connection handles pulled off app.state once."""

    def __init__(self, websocket: WebSocket) -> None:
        self.guardian = websocket.app.state.guardian
        self.bus = getattr(websocket.app.state, "event_bus", None)


@router.websocket("/ws")
async def voice_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    ctx = _Ctx(websocket)

    buffer = bytearray()
    sample_rate = 16_000
    capturing = False

    try:
        while True:
            message = await websocket.receive()

            # Binary frame -> microphone PCM (only while a turn is open).
            data = message.get("bytes")
            if data is not None:
                if capturing:
                    buffer.extend(data)
                    if len(buffer) > _MAX_UTTERANCE_BYTES:
                        await websocket.send_json(
                            {"type": "error", "message": "Utterance too long."}
                        )
                        buffer.clear()
                        capturing = False
                continue

            # Text frame -> control message.
            text = message.get("text")
            if text is None:
                continue  # ignore empty/keepalive frames
            try:
                control = json.loads(text)
            except ValueError:
                continue
            kind = control.get("type")

            if kind == "start":
                buffer.clear()
                capturing = True
                sample_rate = int(control.get("sample_rate", 16_000))
            elif kind == "end":
                if not capturing:
                    continue
                capturing = False
                pcm = bytes(buffer)
                buffer.clear()
                try:
                    await _handle_utterance(websocket, pcm, sample_rate, ctx)
                except Exception as exc:  # noqa: BLE001 — one bad turn shouldn't kill the socket
                    logger.exception("voice turn failed")
                    await websocket.send_json({"type": "error", "message": str(exc)})
            # Unknown control types are ignored so the protocol can grow.
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("voice websocket error")
