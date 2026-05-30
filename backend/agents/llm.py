"""DEPRECATED. Superseded by the provider-neutral seam in backend/llm/.

Kept only so stale imports fail loudly with a clear message instead of pulling
in langchain_ollama. Import the LLM client via:  from backend.llm import build_llm
"""
raise ImportError(
    "backend.agents.llm is removed — use `from backend.llm import build_llm` instead."
)
