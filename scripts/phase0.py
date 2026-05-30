"""Phase 0 runner — text-file-in, text-out, single-agent, OpenAI-backed.

Run from the project root:
    python scripts/phase0.py
    python scripts/phase0.py path/to/input.txt   # process a single file

Prerequisites:
    pip install -e ".[dev]"
    Set OPENAI_API_KEY in .env or the environment.

Controls:
    Enter path to a .txt file  — send its contents to Guardian
    Type your message directly  — interactive mode
    Ctrl-C                      — quit
"""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from backend.agents.guardian import GuardianAgent

logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")


def read_text_file(path: str) -> str:
    p = Path(path.strip())
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    if p.suffix.lower() != ".txt":
        raise ValueError(f"Expected a .txt file, got: {p.suffix}")
    return p.read_text(encoding="utf-8")


def main() -> None:
    logger.info("Initialising Guardian Phase 0 (text mode, OpenAI)…")
    agent = GuardianAgent()

    print()
    print("Guardian Phase 0 — text file mode")
    print("  Type a file path (.txt) to load and send its contents")
    print("  Or type your message directly (no file extension)")
    print("  Ctrl-C to quit")
    print()

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            text = read_text_file(file_path)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}")
            sys.exit(1)

        print(f"[ Loaded: {file_path} ]")
        print(f"  Input    : {text[:120]}{'…' if len(text) > 120 else ''}\n")
        print(f"  Guardian : {agent.chat(text)}\n")
        return

    try:
        while True:
            user_input = input("You (file path or text): ").strip()
            if not user_input:
                continue

            if user_input.endswith(".txt") or Path(user_input).exists():
                try:
                    text = read_text_file(user_input)
                    print(f"  [ Loaded {len(text)} chars from {user_input} ]")
                except (FileNotFoundError, ValueError) as exc:
                    print(f"  Error: {exc}")
                    continue
            else:
                text = user_input

            print(f"  Input    : {text[:120]}{'…' if len(text) > 120 else ''}\n")
            print(f"  Guardian : {agent.chat(text)}\n")

    except KeyboardInterrupt:
        print("\nGuardian shutting down. Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
