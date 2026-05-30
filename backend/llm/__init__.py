"""Provider-agnostic LLM layer.

Public surface — import only from here, never from a vendor SDK:

    from backend.llm import (
        LLMClient, Message, ToolSpec, ToolCall, LLMResponse, build_llm,
    )
"""
from backend.llm.base import (
    Capabilities,
    LLMClient,
    LLMError,
    LLMResponse,
    Message,
    ToolCall,
    ToolSpec,
)
from backend.llm.config import LLMSettings, load_settings
from backend.llm.factory import build_llm

__all__ = [
    "Capabilities",
    "LLMClient",
    "LLMError",
    "LLMResponse",
    "Message",
    "ToolCall",
    "ToolSpec",
    "LLMSettings",
    "load_settings",
    "build_llm",
]
