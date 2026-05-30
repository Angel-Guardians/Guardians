"""Centralised LLM configuration.

ALL model config lives here — model name, endpoint, key, sampling. No literals
(`gpt-4o`, base URLs, keys) anywhere else in the codebase. Swapping OpenAI for a
local DGX Spark endpoint is therefore a `.env` change, nothing more.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class LLMSettings:
    provider: str          # informational label: "openai" | "local" | "nim" | ...
    model: str
    base_url: str
    api_key: str
    temperature: float
    max_tokens: int | None
    supports_tools: bool
    request_timeout: float


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> LLMSettings:
    """Read unified LLM_* env vars, with backward-compatible OpenAI fallbacks."""
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()

    # Unified vars take precedence; fall back to the legacy OPENAI_* names so an
    # existing .env keeps working.
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "not-needed")

    return LLMSettings(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_tokens=(int(os.getenv("LLM_MAX_TOKENS")) if os.getenv("LLM_MAX_TOKENS") else None),
        # Local models vary in tool-calling reliability; let it be turned off per env.
        supports_tools=_bool("LLM_SUPPORTS_TOOLS", True),
        request_timeout=float(os.getenv("LLM_TIMEOUT", "60")),
    )
