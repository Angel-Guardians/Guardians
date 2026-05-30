"""Provider-neutral tracing boundary.

Replaces the OpenAI-specific `langsmith.wrappers.wrap_openai`. Tracing is applied
at the application boundary (the LLMClient.chat call and agent.chat call), so it
covers EVERY backend identically and stays decoupled from any vendor SDK.

If LangSmith is installed and tracing is enabled, real spans are emitted;
otherwise `trace` is a transparent no-op decorator.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])

TRACING_ENABLED = os.getenv("LANGSMITH_TRACING", "").strip().lower() in {"1", "true", "yes", "on"}
_ENABLED = TRACING_ENABLED  # backwards-compatible alias

try:  # optional dependency, optionally enabled
    from langsmith import traceable as _traceable  # type: ignore
except Exception:  # pragma: no cover - langsmith not installed
    _traceable = None


def trace(name: str) -> Callable[[F], F]:
    """Decorator that records a span named `name`, or does nothing if disabled."""

    def decorator(fn: F) -> F:
        if _ENABLED and _traceable is not None:
            return _traceable(name=name)(fn)  # type: ignore[return-value]
        return fn

    return decorator
