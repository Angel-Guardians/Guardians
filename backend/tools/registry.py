"""Tool registry.

Tools register themselves via @register_tool. Sub-agents look up tools
by name and are gated by their allowed_tools set.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from backend.tools.decorators import ToolNotAllowed


_REGISTRY: dict[str, Callable[..., Awaitable[Any]]] = {}


def register_tool(name: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator: make a tool callable by name through the registry."""

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        if name in _REGISTRY:
            raise ValueError(f"tool already registered: {name}")
        _REGISTRY[name] = func
        return func

    return decorator


def get_tool(name: str, *, allowed: set[str] | None = None) -> Callable[..., Awaitable[Any]]:
    if allowed is not None and name not in allowed:
        raise ToolNotAllowed(f"tool {name!r} is not in the allowed set")
    if name not in _REGISTRY:
        raise KeyError(f"unknown tool: {name}")
    return _REGISTRY[name]


def list_tools() -> list[str]:
    return sorted(_REGISTRY)
