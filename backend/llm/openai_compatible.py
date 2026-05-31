"""Adapter for any OpenAI-compatible /v1/chat/completions endpoint.

This single adapter covers:
  - OpenAI cloud            (base_url = https://api.openai.com/v1)
  - vLLM                    (base_url = http://<dgx-spark>:8000/v1)
  - NVIDIA NIM              (base_url = http://<dgx-spark>:8000/v1)
  - Ollama                  (base_url = http://localhost:11434/v1)
  - TGI / LM Studio / etc.

It is the ONLY file permitted to import the `openai` SDK and the only place that
knows the provider wire format. Everything provider-specific (message shaping,
tool-call (de)serialisation, error wrapping) is contained here. To go fully
SDK-free later, swap the SDK calls for raw httpx POSTs — the public surface
(`chat` returning `LLMResponse`) does not change.
"""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.llm.base import (
    Capabilities,
    LLMClient,
    LLMError,
    LLMResponse,
    Message,
    ToolCall,
    ToolSpec,
)
from backend.llm.config import LLMSettings
from backend.llm.tracing import TRACING_ENABLED, trace


class OpenAICompatibleClient(LLMClient):
    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings
        client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.request_timeout,
        )
        # When LangSmith tracing is on, wrap the client so each model call becomes a
        # nested span with prompt/response and token usage — visible under the
        # LangGraph node that made the call. This wrap is the one vendor-specific
        # tracing touch-point, deliberately confined to this adapter; the rest of
        # the app stays SDK-agnostic. Any OpenAI-compatible endpoint (incl. vLLM /
        # NIM on a DGX Spark) is traced the same way.
        if TRACING_ENABLED:
            try:
                from langsmith.wrappers import wrap_openai

                client = wrap_openai(client)
            except Exception:  # pragma: no cover - langsmith absent or incompatible
                pass
        self._client = client
        self._capabilities = Capabilities(supports_tools=settings.supports_tools)

    @property
    def capabilities(self) -> Capabilities:
        return self._capabilities

    # --- public interface --------------------------------------------------------

    @trace(name="llm.chat")
    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        **overrides: Any,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": overrides.pop("model", self._settings.model),
            "messages": [self._encode_message(m) for m in messages],
            "temperature": overrides.pop("temperature", self._settings.temperature),
        }
        max_tokens = overrides.pop("max_tokens", self._settings.max_tokens)
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools and self._capabilities.supports_tools:
            payload["tools"] = [self._encode_tool(t) for t in tools]
        payload.update(overrides)

        # Nemotron (served via trtllm) defaults to reasoning "on", emitting a long
        # <think> block before the answer. Under the router's small max_tokens that
        # empties `content` (every turn falls back to "companion") and it delays /
        # suppresses tool calls. Disable it for local providers. OpenAI cloud rejects
        # unknown body fields, so only do this off-cloud.
        if self._settings.provider != "openai":
            # Ask the server to disable reasoning via the chat template...
            extra_body = payload.get("extra_body") or {}
            extra_body.setdefault("chat_template_kwargs", {"enable_thinking": False})
            payload["extra_body"] = extra_body
            # ...and ALSO inject /no_think into the system prompt, since some trtllm
            # builds (e.g. _autodeploy) ignore chat_template_kwargs. This reaches the
            # model directly via the rendered prompt.
            msgs = payload["messages"]
            if msgs and msgs[0].get("role") == "system":
                if "/no_think" not in (msgs[0].get("content") or ""):
                    msgs[0]["content"] = "/no_think\n" + (msgs[0]["content"] or "")
            else:
                msgs.insert(0, {"role": "system", "content": "/no_think"})

        try:
            raw = self._client.chat.completions.create(**payload)
        except Exception as exc:  # wrap ANY vendor error into a neutral type
            raise LLMError(f"LLM request failed: {exc}") from exc

        return self._decode_response(raw)

    # --- encoding: neutral DTO -> provider wire format ---------------------------

    @staticmethod
    def _encode_message(m: Message) -> dict[str, Any]:
        if m.role == "tool":
            return {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content or ""}
        if m.role == "assistant" and m.tool_calls:
            return {
                "role": "assistant",
                "content": m.content,  # may be None when only tool calls are present
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in m.tool_calls
                ],
            }
        return {"role": m.role, "content": m.content or ""}

    @staticmethod
    def _encode_tool(t: ToolSpec) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
        }

    # --- decoding: provider wire format -> neutral DTO ---------------------------

    @staticmethod
    def _decode_response(raw: Any) -> LLMResponse:
        choice = raw.choices[0]
        msg = choice.message
        tool_calls: list[ToolCall] = []
        for tc in getattr(msg, "tool_calls", None) or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        return LLMResponse(
            text=msg.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            raw=raw,
        )
