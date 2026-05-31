"""Base specialist agent: the Option-B tool-calling loop.

Every specialist inherits this. The loop is written entirely against the neutral
`LLMClient` + DTOs from `backend.llm`, so it is identical whether the backend is
OpenAI cloud or a local model on a DGX Spark. A subclass only provides a
`system_prompt` and a tuple of `tool_names` to bind from the registry.
"""
from __future__ import annotations

import json

from loguru import logger

from backend.llm.base import LLMClient, Message
from backend.tools.registry import ToolRegistry

MAX_TOOL_ROUNDS = 4


class ToolCallingAgent:
    name: str = "base"
    system_prompt: str = ""
    tool_names: tuple[str, ...] = ()
    # Metadata for the TTS / notification layer. Kept as plain strings so the agent
    # layer stays decoupled from the DB (SeverityTier) and voice enums; the
    # dispatcher maps voice_profile -> a Kokoro voice id (see agents/voice_profiles.py)
    # and uses escalation_ceiling to cap how loud an agent is allowed to get.
    voice_profile: str = "calm"          # calm | urgent | gentle | firm | formal | cloned_family
    escalation_ceiling: str = "tier_2_nudge"  # tier_1_whisper..tier_4_call

    def __init__(self, llm: LLMClient, registry: ToolRegistry) -> None:
        self._llm = llm
        self._registry = registry

    def chat(self, user_message: str, history: list[Message], emit=None) -> str:
        """Run the tool loop. `emit(kind, payload)` is an optional progress hook
        (kind == "tool_invocation") so the live dashboard can light up each tool
        the instant it fires; safe to omit for headless runs (phase0, tests)."""
        messages: list[Message] = [
            Message(role="system", content=self.system_prompt),
            *history,
            Message(role="user", content=user_message),
        ]
        tools = self._registry.specs(self.tool_names) or None

        response = None
        for _ in range(MAX_TOOL_ROUNDS):
            response = self._llm.chat(messages, tools=tools)

            if not response.tool_calls:
                return response.text or ""

            # Echo the assistant's tool-call turn, then run each stub and feed the
            # results back so the model can compose a final spoken reply.
            messages.append(
                Message(role="assistant", content=response.text, tool_calls=response.tool_calls)
            )
            for call in response.tool_calls:
                result = self._registry.execute(call.name, call.arguments)
                if emit is not None:
                    emit(
                        "tool_invocation",
                        {"tool": call.name, "args": call.arguments, "result": result},
                    )
                messages.append(
                    Message(role="tool", tool_call_id=call.id, content=json.dumps(result))
                )

        logger.warning(f"[{self.name}] hit MAX_TOOL_ROUNDS; returning last text")
        return (response.text if response else "") or "(no response)"
