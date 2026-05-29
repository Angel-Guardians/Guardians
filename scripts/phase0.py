"""Phase 0 runner — voice-in, voice-out, single-agent.

Run from the project root:
    python scripts/phase0.py

Prerequisites:
    pip install -e ".[dev]"
    ollama pull llama3.1:8b-instruct-q4_K_M

Controls:
    Enter       — start recording
    Enter again — stop recording and send to Guardian
    Ctrl-C      — quit
"""
from __future__ import annotations

import sys

from langchain_core.messages import HumanMessage
from loguru import logger

from backend.agents.guardian import build_guardian_graph
from backend.always_on.capture import AudioPipeline
from backend.tools.action.tts import speak

# Simple stderr-only logging for the Phase 0 script (no logs/ dir required).
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")


def main() -> None:
    logger.info("Initialising Guardian Phase 0…")

    pipeline = AudioPipeline()
    graph = build_guardian_graph()
    history: list = []  # conversation history — grows with each turn

    speak("Guardian is online. Press Enter to speak, then press Enter again when you are done.")

    print()
    print("Guardian Phase 0 — push to talk")
    print("  Enter  : start / stop recording")
    print("  Ctrl-C : quit")
    print()

    try:
        while True:
            input("[ Press Enter to START talking ]")
            print("  (recording…)")
            pipeline.start_recording()

            input("[ Press Enter to STOP talking  ]")
            print("  (transcribing…)")
            text = pipeline.stop_and_transcribe().strip()

            if not text:
                print("  (nothing heard — try again)\n")
                continue

            print(f"\n  You      : {text}")
            history.append(HumanMessage(content=text))

            print("  Guardian : ", end="", flush=True)
            result = graph.invoke({"messages": history})
            reply: str = result["messages"][-1].content
            history = result["messages"]  # keep full history for multi-turn context
            print(reply)
            print()

            speak(reply)

    except KeyboardInterrupt:
        print("\nGuardian shutting down. Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
