"""Person-history recall (RAG).

`recall_history` retrieves relevant facts from a patient's life-history note
(data/personas/<id>.md). Two backends, chosen automatically:

  * pgvector  — if MEMORY_BACKEND=pgvector and embeddings are configured, chunks
                are embedded and queried by cosine similarity (see backend/memory).
  * keyword   — the always-available fallback: split the markdown into paragraphs
                and score by query word overlap. No DB, no network, runs anywhere.

Same tool signature either way, so agents and the demo never change when you turn
the vector store on.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from backend.llm.base import ToolSpec

_PERSONA_DIR = Path(__file__).resolve().parents[2] / "data" / "personas"


def _keyword_recall(query: str, persona_id: str, k: int) -> list[str]:
    path = _PERSONA_DIR / f"{persona_id}.md"
    if not path.exists():
        # fall back to the first persona file available
        candidates = sorted(_PERSONA_DIR.glob("*.md"))
        if not candidates:
            return []
        path = candidates[0]
    text = path.read_text(encoding="utf-8")
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    q_words = {w for w in re.findall(r"[a-z']+", query.lower()) if len(w) > 2}
    scored = []
    for p in paras:
        p_words = set(re.findall(r"[a-z']+", p.lower()))
        overlap = len(q_words & p_words)
        if overlap:
            scored.append((overlap, p))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [p for _, p in scored[:k]] or paras[:k]


def recall_history(query: str, persona_id: str = "eleanor", k: int = 3) -> dict[str, Any]:
    """Retrieve up to `k` relevant snippets from the patient's life-history note."""
    backend = os.getenv("MEMORY_BACKEND", "keyword").strip().lower()
    if backend == "pgvector":
        try:
            from backend.memory.vector_store import recall as vector_recall

            snippets = vector_recall(query, persona_id, k)
            return {"tool": "recall_history", "backend": "pgvector", "snippets": snippets}
        except Exception:  # pragma: no cover - degrade to keyword if store unavailable
            pass
    return {
        "tool": "recall_history",
        "backend": "keyword",
        "snippets": _keyword_recall(query, persona_id, k),
    }


def register(registry) -> None:
    registry.register(
        ToolSpec(
            name="recall_history",
            description="Recall relevant facts from the patient's life history and past "
            "conversations (family, routines, preferences, prior incidents).",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to recall about the patient."},
                    "persona_id": {"type": "string", "description": "Patient id, e.g. 'eleanor'."},
                },
                "required": ["query"],
            },
        ),
        recall_history,
    )
