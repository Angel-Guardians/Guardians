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

from backend.events.log import persist_event_log
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
        # Write to the Event Log BEFORE routing (ARCHITECTURE.md sec. 3.3).
        # `tool_invocation` events are skipped here: they're persisted at the tool
        # boundary by @audit_log (with full args + result), so the trail stays
        # complete on headless / event-driven paths that never reach this bus.
        event_type = getattr(event, "type", event.__class__.__name__)
        if event_type != "tool_invocation":
            persist_event_log(
                source=event.source,
                event_type=event_type,
                payload=event.to_log_payload(),
                severity=event.severity,
                incident_id=event.incident_id,
            )
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
