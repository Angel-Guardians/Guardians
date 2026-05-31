"""Tool registry.

A tool is a `ToolSpec` (advertised to the model) bound to a plain Python callable
that returns a JSON-serialisable dict. For the hackathon every callable is a stub
returning a canned response; swapping a stub for a real integration (Twilio, FHIR,
911 dispatch) is a one-function change with no impact on agents or the LLM layer.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger

from backend.llm.base import ToolSpec

ToolFn = Callable[..., dict[str, Any]]


@dataclass
class Tool:
    spec: ToolSpec
    fn: ToolFn


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, spec: ToolSpec, fn: ToolFn) -> None:
        self._tools[spec.name] = Tool(spec, fn)

    def spec(self, name: str) -> ToolSpec:
        return self._tools[name].spec

    def specs(self, names: tuple[str, ...]) -> list[ToolSpec]:
        return [self._tools[n].spec for n in names if n in self._tools]

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self._tools:
            logger.warning(f"[tool] unknown tool requested: {name}")
            return {"error": f"unknown tool: {name}"}
        logger.info(f"[tool] -> {name}({arguments})")
        result = self._tools[name].fn(**arguments)
        logger.info(f"[tool] <- {name} {result}")
        return result


def build_default_registry() -> ToolRegistry:
    """Register every stub. Imported lazily to avoid circulars."""
    from backend.tools import civic, emergency, general_tools, health, memory, reminder

    registry = ToolRegistry()
    for module in (emergency, general_tools, health, reminder, civic, memory):
        module.register(registry)
    return registry
