"""Cross-cutting decorators for side-effecting / egress tools.

@audit_log     - persists a tool_invocation row to the Event Log (before + after)
@idempotent    - dedupes identical calls within a sliding window (no double-dial)
@consent_check - looks up the patient's ConsentMatrix before allowing egress

These are applied at the tool boundary so individual tool authors cannot forget.
See ARCHITECTURE.md sec. 3.6 (consent) and sec. 3.8 (audit).

NOTE: tools in this codebase are **synchronous** callables invoked by
``ToolRegistry.execute``; these decorators are therefore synchronous too. They
degrade gracefully — a consent-lookup or audit-write failure logs a warning and
lets the call proceed, so logging never takes down a live turn.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from loguru import logger

from backend.events.log import persist_event_log

ToolFn = Callable[..., dict[str, Any]]


def _safe(value: Any) -> Any:
    """Best-effort JSON-friendly copy for storing in the Event Log payload."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


# ---------------------------------------------------------------------------
# @audit_log — persist every invocation to the Event Log
# ---------------------------------------------------------------------------


def audit_log(func: ToolFn) -> ToolFn:
    """Wrap a tool; write a ``tool_invocation`` Event Log row after it runs."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        source = f"tool.{func.__name__}"
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            persist_event_log(
                source=source,
                event_type="tool_invocation",
                payload={"tool": func.__name__, "args": _safe(kwargs), "error": str(exc)},
                reason="tool raised",
            )
            logger.exception(f"tool:fail {func.__name__}")
            raise
        persist_event_log(
            source=source,
            event_type="tool_invocation",
            payload={"tool": func.__name__, "args": _safe(kwargs), "result": _safe(result)},
        )
        return result

    return wrapper


# ---------------------------------------------------------------------------
# @idempotent — suppress identical calls within a window
# ---------------------------------------------------------------------------

_IDEMPOTENCY: dict[str, float] = {}


def reset_idempotency() -> None:
    """Clear the dedup cache (tests / between sessions)."""
    _IDEMPOTENCY.clear()


def idempotent(
    *, window_seconds: int = 60
) -> Callable[[ToolFn], ToolFn]:
    """Dedupe identical calls within a sliding window.

    Tools with real-world side effects (call_911, notify_caregiver, call_person)
    MUST be decorated with this so a retry — or the model emitting the same call
    twice in one turn — does not double-dial. The dedup key is the tool name plus
    its keyword arguments; a duplicate returns a ``duplicate_suppressed`` marker
    instead of re-firing.
    """

    def decorator(func: ToolFn) -> ToolFn:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            key = f"{func.__name__}:{json.dumps(kwargs, sort_keys=True, default=str)}"
            now = time.monotonic()
            last = _IDEMPOTENCY.get(key)
            if last is not None and (now - last) < window_seconds:
                logger.warning(
                    f"[idempotent] suppressed duplicate {func.__name__} "
                    f"within {window_seconds}s"
                )
                return {
                    "tool": func.__name__,
                    "status": "duplicate_suppressed",
                    "note": f"identical call within {window_seconds}s was not repeated",
                }
            _IDEMPOTENCY[key] = now
            try:
                return func(*args, **kwargs)
            except Exception:
                # Don't let a failed attempt block a genuine retry.
                _IDEMPOTENCY.pop(key, None)
                raise

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# @consent_check — enforce the patient's ConsentMatrix before egress
# ---------------------------------------------------------------------------


def _consent_allows(recipient: str, data_category: str) -> bool:
    """True unless a ConsentMatrix row explicitly sets this pair to 'never'.

    Fail-open: with no patient or no matching row (the default seeded state), the
    egress is allowed. The gate only blocks when the patient has deliberately set
    the recipient/category mode to 'never'.
    """
    try:
        from sqlmodel import Session, select

        from backend.db.models import ConsentMatrix, Patient
        from backend.db.session import engine

        with Session(engine) as session:
            from backend.tools._active_patient import get_active_patient

            patient_id = get_active_patient() or session.exec(
                select(Patient.id).order_by(Patient.id)
            ).first()
            if patient_id is None:
                return True
            row = session.exec(
                select(ConsentMatrix)
                .where(ConsentMatrix.patient_id == patient_id)
                .where(ConsentMatrix.recipient == recipient)
                .where(ConsentMatrix.data_category == data_category)
            ).first()
            if row is None:
                return True
            return row.mode != "never"
    except Exception as exc:  # noqa: BLE001 - never block egress on a lookup bug
        logger.warning(f"[consent_check] lookup failed for {recipient}/{data_category}: {exc}")
        return True


def consent_check(
    *, recipient: str, data_category: str
) -> Callable[[ToolFn], ToolFn]:
    """Verify the patient's ConsentMatrix allows this egress.

    Tools that talk to a human outside the home should be decorated with this.
    When the matrix blocks the egress, the call is NOT made; a structured
    ``blocked_by_consent`` marker is returned so the agent can respond gracefully
    instead of the turn crashing.
    """

    def decorator(func: ToolFn) -> ToolFn:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            if not _consent_allows(recipient, data_category):
                logger.warning(
                    f"[consent_check] blocked {func.__name__}: "
                    f"{recipient}/{data_category} set to 'never'"
                )
                return {
                    "tool": func.__name__,
                    "status": "blocked_by_consent",
                    "recipient": recipient,
                    "data_category": data_category,
                    "note": "patient consent matrix blocks this recipient/category",
                }
            return func(*args, **kwargs)

        return wrapper

    return decorator


class ConsentDenied(RuntimeError):
    """Raised by callers that want strict (non-graceful) consent enforcement."""

    def __init__(self, recipient: str, data_category: str, reason: str) -> None:
        super().__init__(f"consent denied: {recipient}/{data_category} - {reason}")
        self.recipient = recipient
        self.data_category = data_category
        self.reason = reason


class ToolNotAllowed(RuntimeError):
    """Raised when a sub-agent attempts a tool outside its allowed set."""
