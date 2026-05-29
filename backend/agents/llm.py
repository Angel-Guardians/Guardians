"""LLM client wrappers.

Two clients: generalist (Llama 3.1 8B) and clinical (Meditron 7B).
A tiny classifier client (Phi-3.5-mini) is also exposed for the Risk
Classifier and Router.

All three speak to Ollama for the hackathon. Phase 7 swaps generalist
to NIM/TensorRT-LLM behind the same interface.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from backend.config import settings

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


def get_generalist_llm() -> "BaseChatModel":
    """Llama 3.1 8B - powers every conversational sub-agent."""
    from langchain_ollama import ChatOllama

    return ChatOllama(base_url=settings.ollama_base_url, model=settings.llm_model_generalist)


def get_clinical_llm() -> "BaseChatModel":
    """Meditron 7B - exposed to Health Agent as a `clinical_consult` tool."""
    from langchain_ollama import ChatOllama

    return ChatOllama(base_url=settings.ollama_base_url, model=settings.llm_model_clinical)


def get_classifier_llm() -> "BaseChatModel":
    """Phi-3.5-mini - cheap classifier for routing and risk scoring."""
    from langchain_ollama import ChatOllama

    return ChatOllama(base_url=settings.ollama_base_url, model=settings.llm_model_classifier)
