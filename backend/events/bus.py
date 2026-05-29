"""Event bus.

Hackathon: in-process asyncio queues with pub-sub fan-out.
Production: swap to NATS or Redis Streams behind the same interface.

Every event is written to the Event Log BEFORE being routed.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable

from loguru import logger

from backend.events.types import GuardianEvent


EventHandler = Callable[[GuardianEvent], Awaitable[None]]


class EventBus:
    """In-process pub-sub. Subscribe with `bus.subscribe(handler)`."""

    def __init__(self) -> None:
        self._subscribers: list[EventHandler] = []
        self._typed_subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[GuardianEvent] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    def subscribe(self, handler: EventHandler, event_type: str | None = None) -> None:
        if event_type is None:
            self._subscribers.append(handler)
        else:
            self._typed_subscribers[event_type].append(handler)

    async def publish(self, event: GuardianEvent) -> None:
        """Persist-then-publish. The persistence step is the audit trail."""
        # TODO: write to EventLogEntry BEFORE routing (ARCHITECTURE.md sec. 3.3)
        await self._queue.put(event)

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="event_bus_run")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        while True:
            event = await self._queue.get()
            handlers = list(self._subscribers)
            handlers.extend(self._typed_subscribers.get(event.__class__.__name__, []))
            for handler in handlers:
                try:
                    await handler(event)
                except Exception:  # noqa: BLE001
                    logger.exception(f"handler {handler!r} failed on {event!r}")

    async def stream(self) -> AsyncIterator[GuardianEvent]:
        """SSE-friendly stream. Each subscriber gets its own queue."""
        local_queue: asyncio.Queue[GuardianEvent] = asyncio.Queue()

        async def relay(event: GuardianEvent) -> None:
            await local_queue.put(event)

        self.subscribe(relay)
        try:
            while True:
                yield await local_queue.get()
        finally:
            if relay in self._subscribers:
                self._subscribers.remove(relay)
