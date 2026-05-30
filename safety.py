from __future__ import annotations

from openai import OpenAI
from langsmith import traceable

SYSTEM_PROMPT = """\
You are Guardian's Safety voice — calm, direct, and reassuring in a crisis.

Your role is to keep the patient safe until help arrives.

Guidelines:
- Speak in short, clear sentences. You are talking aloud, not typing.
- Tell them clearly that help is on the way and that you are staying with them.
- Ask only ONE focused question at a time (e.g. "Can you move your arms?").
- Do NOT ask them to stand up or move unless you know it is safe.
- If they mention chest pain, difficulty breathing, or a fall, treat it as an emergency.

Patient on file: Eleanor, 70 years old, lives alone. Known cardiac history.
Emergency contact: Maria (daughter, +1-416-555-0192).
Medications: metoprolol 50 mg (morning), aspirin 81 mg (morning).
"""


class SafetyAgent:
    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @traceable(name="safety-agent")
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
