"""Provider-neutral LLM interface.

Nothing in `backend/agents` or `backend/tools` should import a vendor SDK.
They depend only on the dataclasses and the `LLMClient` protocol defined here.
A provider's native request/response objects must never cross out of an adapter
(see `backend/llm/openai_compatible.py`); only these DTOs do.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# --- Neutral message / tool DTOs -------------------------------------------------


@dataclass
class Message:
    """A single chat turn, independent of any provider wire format."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str | None = None
    tool_calls: list["ToolCall"] = field(default_factory=list)
    tool_call_id: str | None = None  # set on role == "tool"


@dataclass
class ToolSpec:
    """What an agent advertises to the model."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for the arguments object


@dataclass
class ToolCall:
    """What the model asks the application to run."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Normalised model output. `raw` is adapter-private and never read by core."""

    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    raw: Any = None


@dataclass(frozen=True)
class Capabilities:
    """Declares what a backend can do so agents can degrade gracefully."""

    supports_tools: bool = True
    supports_json_mode: bool = False
    max_context: int = 8192


# --- Errors ----------------------------------------------------------------------


class LLMError(RuntimeError):
    """Provider-neutral error. Adapters wrap vendor exceptions into this so core
    code never catches `openai.*` (or any other SDK) exception types."""


# --- The single interface the rest of the app talks to ---------------------------


@runtime_checkable
class LLMClient(Protocol):
    """The one interface agents depend on. Implemented per backend."""

    @property
    def capabilities(self) -> Capabilities: ...

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        **overrides: Any,  # temperature, max_tokens, etc.
    ) -> LLMResponse: ...
