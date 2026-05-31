"""Live fan-out of the watch's microphone stream to dashboard listeners.

The voice WebSocket (backend/api/voice.py) feeds every inbound PCM frame and the
turn's control events here; any number of browsers connected to `/voice/listen`
receive them and play the audio through the Live page's speaker.

In-process and best-effort: a slow listener has its oldest frame dropped rather
than back-pressuring the watch. This mirrors the EventBus design — swap to NATS /
Redis behind the same interface for multi-process later.
"""
from __future__ import annotations

import asyncio

# Queue item: ("audio", pcm_bytes) or ("event", json_dict).
_Item = tuple[str, object]


class VoiceMonitor:
    """Broadcasts the live mic stream to subscribed dashboard sockets."""

    def __init__(self) -> None:
        self._listeners: set[asyncio.Queue[_Item]] = set()

    def subscribe(self) -> asyncio.Queue[_Item]:
        queue: asyncio.Queue[_Item] = asyncio.Queue(maxsize=256)
        self._listeners.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[_Item]) -> None:
        self._listeners.discard(queue)

    @property
    def has_listeners(self) -> bool:
        return bool(self._listeners)

    def _fan_out(self, item: _Item) -> None:
        for queue in list(self._listeners):
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                # Drop the oldest frame so live audio stays current.
                try:
                    queue.get_nowait()
                    queue.put_nowait(item)
                except asyncio.QueueEmpty:
                    pass

    def broadcast_audio(self, pcm: bytes) -> None:
        self._fan_out(("audio", pcm))

    def broadcast_event(self, data: dict) -> None:
        self._fan_out(("event", data))
