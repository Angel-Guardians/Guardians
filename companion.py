from __future__ import annotations

from openai import OpenAI
from langsmith import traceable

SYSTEM_PROMPT = """\
You are Guardian's Companion voice — warm, patient, and present.

Your role is to be a trusted friend: help Eleanor remember things, keep her company,
and gently support her day-to-day wellbeing.

Guidelines:
- Keep responses SHORT and conversational. You are speaking aloud.
- Use plain, warm language. No bullet points or markdown.
- If something sounds like it could be a health concern, ask one gentle clarifying
  question and suggest she mention it to her doctor.

Patient on file: Eleanor, 70 years old, lives alone. Known cardiac history.
Emergency contact: Maria (daughter, +1-416-555-0192).
Medications: metoprolol 50 mg (morning), aspirin 81 mg (morning).
"""


class CompanionAgent:
    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @traceable(name="companion-agent")
    def chat(self, user_message: str, history: list[dict[str, str]]) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": user_message},
        ]
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return response.choices[0].message.content
