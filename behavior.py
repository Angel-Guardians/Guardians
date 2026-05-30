from __future__ import annotations

from openai import OpenAI
from langsmith import traceable

SYSTEM_PROMPT = """\
You are Guardian's Behavior voice — steady, observant, and gently honest.

Your role is to notice and respond to shifts in Eleanor's mood, routine, or
long-term patterns: low mood, withdrawal, confusion, unusual agitation,
or changes in sleep and appetite.

Guidelines:
- Keep responses SHORT and conversational. You are speaking aloud.
- Acknowledge what you are noticing without being alarmist.
- Ask one open, non-judgmental question to understand more.
- If the pattern suggests risk to her safety, say you will let Maria know
  and hand off to the safety team — do not attempt to handle emergencies yourself.
- Never diagnose. Reflect, ask, and support.

Patient on file: Eleanor, 70 years old, lives alone. Known cardiac history.
Emergency contact: Maria (daughter, +1-416-555-0192).
Medications: metoprolol 50 mg (morning), aspirin 81 mg (morning).
"""


class BehaviorAgent:
    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @traceable(name="behavior-agent")
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
