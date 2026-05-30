"""Factory: config -> LLMClient.

The only place that decides which adapter to instantiate. Today every supported
backend (OpenAI cloud, vLLM, NIM, Ollama) speaks the OpenAI-compatible protocol,
so they all use one adapter and differ only by `.env`. A genuinely non-compatible
provider later means adding one branch here and one new adapter file — no changes
to agents or tools.
"""
from __future__ import annotations

from backend.llm.base import LLMClient
from backend.llm.config import LLMSettings, load_settings
from backend.llm.openai_compatible import OpenAICompatibleClient


def build_llm(settings: LLMSettings | None = None) -> LLMClient:
    settings = settings or load_settings()
    # All current providers are OpenAI-compatible; switch on provider only when a
    # non-compatible backend is actually added.
    return OpenAICompatibleClient(settings)
