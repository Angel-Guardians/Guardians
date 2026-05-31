"""Event Log persistence — the append-only audit trail (ARCHITECTURE.md sec. 3.3).

`persist_event_log` is the single sync writer for ``EventLogEntry`` rows. It is
called from two places:

  * ``EventBus.publish`` — every turn-envelope event (transcript, routing
    decision, agent reply, …) is persisted before it is fanned out to streaming
    subscribers ("persist-then-publish").
  * ``@audit_log`` (tools/decorators.py) — each tool invocation is logged at the
    tool boundary, so the trail is complete even on headless / event-driven paths
    that never touch the async bus.

It is deliberately best-effort: a logging failure must never break a turn, so all
exceptions are swallowed with a warning.
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from backend.db.models import EventLogEntry, SeverityTier
from backend.db.session import engine
from sqlmodel import Session


def persist_event_log(
    *,
    source: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    severity: SeverityTier | None = None,
    incident_id: int | None = None,
    reason: str | None = None,
) -> int | None:
    """Append one row to the Event Log. Returns the new row id, or None on failure."""
    try:
        with Session(engine) as session:
            entry = EventLogEntry(
                source=source,
                event_type=event_type,
                payload=payload or {},
                severity=severity,
                incident_id=incident_id,
                reason=reason,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry.id
    except Exception as exc:  # noqa: BLE001 - audit logging must never break a turn
        logger.warning(f"[event_log] failed to persist {event_type} from {source}: {exc}")
        return None
