"""The Shared Tool Bus.

Four buckets: sensing, memory_reasoning, action, integrations. Every
tool is a Pydantic-typed function. Buckets are organizational; gating
is per-agent (see backend.agents.<name>.allowed_tools).
"""
