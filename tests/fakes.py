"""Test doubles for the LLM layer.

`FakeLLM` implements the `LLMClient` interface with a scripted queue of responses,
so the whole agent/router/tool loop can be exercised offline with zero network and
no API key. Because every adapter must satisfy the same `LLMClient` contract, a
test written against `FakeLLM` is also a contract test for the real adapter.
"""
from __future__ import annotations

from collections import deque

from backend.llm.base import Capabilities, LLMResponse, Message, ToolSpec


class FakeLLM:
    """Returns queued LLMResponses in order; records what it was asked."""

    def __init__(self, scripted: list[LLMResponse]) -> None:
        self._queue: deque[LLMResponse] = deque(scripted)
        self.calls: list[dict] = []
        self._capabilities = Capabilities(supports_tools=True)

    @property
    def capabilities(self) -> Capabilities:
        return self._capabilities

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        **overrides: object,
    ) -> LLMResponse:
        self.calls.append({"messages": messages, "tools": tools, "overrides": overrides})
        if not self._queue:
            return LLMResponse(text="(fake: no more scripted responses)")
        return self._queue.popleft()
