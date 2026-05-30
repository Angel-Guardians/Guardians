"""Phase 0 — single Guardian agent.

Direct OpenAI SDK calls, no graph framework.
Phase 2 splits this into Orchestrator + SafetyAgent + CompanionAgent.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv
from openai import OpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai

load_dotenv()

SYSTEM_PROMPT = """\
You are Guardian, a calm and caring AI companion living in the patient's home.
Your role is to be a trusted presence — keeping the patient safe, helping them
remember things, and being there when they need someone to talk to.

Guidelines:
- Keep responses SHORT and clear. You are speaking aloud, not typing.
- Use plain, warm language. Avoid bullet points or markdown.
- If the patient sounds distressed or mentions a physical symptom, ask one
  focused clarifying question.
- If they describe a fall, chest pain, difficulty breathing, or an emergency,
  tell them clearly that help is coming and stay with them.

Patient on file: Eleanor, 70 years old, lives alone. Known cardiac history.
Emergency contact: Maria (daughter, +1-416-555-0192).
Medications: metoprolol 50 mg (morning), aspirin 81 mg (morning).
"""


class GuardianAgent:
    def __init__(self) -> None:
        self._client = wrap_openai(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self._history: list[dict[str, str]] = []

    @traceable(name="guardian-chat")
    def chat(self, user_message: str) -> str:
        self._history.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self._history]
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        reply: str = response.choices[0].message.content
        self._history.append({"role": "assistant", "content": reply})
        return reply
