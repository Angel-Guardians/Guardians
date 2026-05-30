"""Live smoke test: does the real model decide to call the right tools?

Runs a few inputs through the real GuardianAgent (model from your .env) and prints,
per turn: the chosen route, which tools the MODEL chose to call, and the final reply.
Unlike the pytest suite (which uses a scripted FakeLLM), this exercises real
model-driven tool selection.

Usage:
    # set LLM_API_KEY (and LLM_MODEL=gpt-4o) in .env first
    uv run python scripts/try_live.py
"""
from __future__ import annotations

from backend.agents.guardian import GuardianAgent
from backend.tools import emergency, health, reminder

# Every stub appends to one of these module-level logs when the model calls it.
_LOGS = (emergency.CALL_LOG, health.CALL_LOG, reminder.CALL_LOG)

INPUTS = [
    "I was reaching for a shelf, lost my balance, and now my chest feels tight.",
    "What time am I supposed to take my pills today?",
    "Can you text my daughter Maria that I'm feeling a bit lonely today?",
    "My heart rate monitor says 110, is that normal?",
    "It's a lovely morning. How are you?",
]


def _snapshot() -> list[dict]:
    out: list[dict] = []
    for log in _LOGS:
        out.extend(log)
    return out


def main() -> None:
    guardian = GuardianAgent()  # real LLM from .env
    for text in INPUTS:
        for log in _LOGS:
            log.clear()

        route = guardian.route(text)
        reply = guardian.chat(text)
        tools_called = [f"{e['tool']}({ {k: v for k, v in e.items() if k != 'tool'} })"
                        for e in _snapshot()]

        print("\n" + "=" * 70)
        print(f"INPUT : {text}")
        print(f"ROUTE : {route}")
        print(f"TOOLS : {tools_called or 'none — model chose not to call a tool'}")
        print(f"REPLY : {reply}")


if __name__ == "__main__":
    main()
