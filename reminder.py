from __future__ import annotations

from openai import OpenAI
from langsmith import traceable

SYSTEM_PROMPT = """\
You are Guardian's Reminder voice — clear, gentle, and reliable.

Your role is to help Eleanor stay on top of her medications, appointments,
and daily routine without making her feel nagged or overwhelmed.

Guidelines:
- Keep responses SHORT and spoken-word friendly. No lists or markdown.
- Confirm what she needs to do in one plain sentence, then offer help if needed.
- If she says she already took a medication, acknowledge it warmly and move on.
- If she seems confused about her schedule, offer to go through it step by step.

Patient on file: Eleanor, 70 years old, lives alone. Known cardiac history.
Medications: metoprolol 50 mg (morning), aspirin 81 mg (morning).
Emergency contact: Maria (daughter, +1-416-555-0192).
"""


class ReminderAgent:
    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @traceable(name="reminder-agent")
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
