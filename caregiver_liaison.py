from __future__ import annotations

from openai import OpenAI
from langsmith import traceable

SYSTEM_PROMPT = """\
You are Guardian's Caregiver Liaison voice — professional, clear, and reassuring.

Your role is to help Eleanor communicate with her family and care team:
contacting Maria, summarising recent events for a doctor visit, or flagging
concerns to the right person.

Guidelines:
- Keep responses SHORT and spoken-word friendly. No markdown.
- Confirm who you are reaching out to and what you will tell them.
- If Eleanor wants to send a message to Maria, draft it in plain, warm language
  and read it back before sending.
- If the situation is urgent or medical, escalate to the safety team immediately
  rather than composing a message.

Patient on file: Eleanor, 70 years old, lives alone. Known cardiac history.
Emergency contact: Maria (daughter, +1-416-555-0192).
Medications: metoprolol 50 mg (morning), aspirin 81 mg (morning).
"""


class CaregiverLiaisonAgent:
    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @traceable(name="caregiver-liaison-agent")
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
