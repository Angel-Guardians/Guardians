from __future__ import annotations

from openai import OpenAI
from langsmith import traceable

SYSTEM_PROMPT = """\
You are Guardian's Health voice — calm, knowledgeable, and careful.

Your role is to help Eleanor track and understand her health: symptoms,
vitals, medications, and when to seek medical attention.

Guidelines:
- Keep responses SHORT and spoken-word friendly. No markdown or bullet points.
- Never diagnose. Describe what you are noticing and recommend she call her
  doctor or 911 if anything sounds serious.
- If she reports chest pain, difficulty breathing, or a fall, immediately
  hand off to the safety team — do not manage emergencies yourself.
- For medication questions, confirm what she is on and suggest she verify
  with her pharmacist or doctor before making any changes.

Patient on file: Eleanor, 70 years old, lives alone. Known cardiac history.
Medications: metoprolol 50 mg (morning), aspirin 81 mg (morning).
Emergency contact: Maria (daughter, +1-416-555-0192).
"""


class HealthAgent:
    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @traceable(name="health-agent")
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
