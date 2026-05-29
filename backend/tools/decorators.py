"""Cross-cutting decorators for every tool on the bus.

@audit_log     - writes a ToolInvocationEvent to the Event Log
@idempotent    - dedupes by idempotency key for a window
@consent_check - looks up the patient's ConsentMatrix before allowing egress

These are applied at the tool boundary so individual tool authors cannot
forget. See ARCHITECTURE.md sec. 3.6 and sec. 3.8.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from loguru import logger


P = ParamSpec("P")
R = TypeVar("R")


def audit_log(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Wrap a tool call; emit ToolInvocationEvent before + after."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # TODO: write start ToolInvocationEvent to bus
        logger.info(f"tool:start {func.__name__}")
        try:
            result = await func(*args, **kwargs)
        except Exception:
            logger.exception(f"tool:fail {func.__name__}")
            raise
        # TODO: write end ToolInvocationEvent with result summary
        logger.info(f"tool:end {func.__name__}")
        return result

    return wrapper


def idempotent(
    *, key_field: str = "idempotency_key", window_seconds: int = 60
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Dedupe by idempotency key within a sliding window.

    Tools that have side effects (call_911, send_sms, fhir_push) MUST be
    decorated with this so retries do not double-dial.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # TODO: check Redis or in-process LRU for the idempotency key
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def consent_check(
    *, recipient: str, data_category: str
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Verify the patient's ConsentMatrix allows this egress.

    Tools that talk to any human outside the home MUST be decorated with
    this. See ARCHITECTURE.md sec. 3.6.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # TODO: look up ConsentMatrix row; raise ConsentDenied if blocked
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class ConsentDenied(RuntimeError):
    """Raised by @consent_check when the matrix blocks an egress."""

    def __init__(self, recipient: str, data_category: str, reason: str) -> None:
        super().__init__(f"consent denied: {recipient}/{data_category} - {reason}")
        self.recipient = recipient
        self.data_category = data_category
        self.reason = reason


class ToolNotAllowed(RuntimeError):
    """Raised when a sub-agent attempts a tool outside its allowed set."""
