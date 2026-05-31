"""Resolve the OpenAI API key for voice STT/TTS.

Both Whisper (STT) and the TTS endpoint need a real OpenAI key. The project has
two places a key can live: the dedicated ``OPENAI_API_KEY`` and the unified
``LLM_API_KEY`` used by the chat model. A common setup leaves ``OPENAI_API_KEY``
as the ``.env.example`` placeholder while ``LLM_API_KEY`` holds the real key — in
which case voice should just reuse it (same OpenAI account, same key works for
chat, Whisper, and TTS).

So: prefer a real ``OPENAI_API_KEY``; otherwise fall back to ``LLM_API_KEY`` when
the LLM is actually pointed at OpenAI.
"""
from __future__ import annotations

from backend.config import settings
from backend.llm.config import load_settings

# Placeholders shipped in .env.example / defaults that are not real keys.
_PLACEHOLDERS = {"", "sk-replace-me", "not-needed", "changeme", "your-api-key"}


def looks_real(key: str | None) -> bool:
    if not key:
        return False
    k = key.strip()
    return k.lower() not in _PLACEHOLDERS and not k.lower().startswith("sk-replace")


def openai_api_key() -> str | None:
    """Best available OpenAI key, or None if neither source has a real one."""
    if looks_real(settings.openai_api_key):
        return settings.openai_api_key

    llm = load_settings()
    points_at_openai = llm.provider == "openai" or "api.openai.com" in (llm.base_url or "")
    if points_at_openai and looks_real(llm.api_key):
        return llm.api_key

    return None
