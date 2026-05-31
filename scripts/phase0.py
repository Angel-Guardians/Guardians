"""Phase 0 runner — text-file-in, text-out, single-agent, OpenAI-backed.

Run from the project root:
    uv run scripts/phase0.py                        # default patient (id=1)
    uv run scripts/phase0.py --patient Sarah        # by name
    uv run scripts/phase0.py --patient-id 2         # by id
    uv run scripts/phase0.py path/to/input.txt      # process a single file

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


def resolve_patient_id(args: list[str]) -> tuple[int, list[str]]:
    """Extract --patient <name> or --patient-id <id> from args, return (id, remaining_args)."""
    from sqlmodel import Session, select
    from backend.db.models import Patient
    from backend.db.session import engine

    remaining = list(args)

    if "--patient-id" in remaining:
        idx = remaining.index("--patient-id")
        patient_id = int(remaining[idx + 1])
        del remaining[idx:idx + 2]
        return patient_id, remaining

    if "--patient" in remaining:
        idx = remaining.index("--patient")
        name = remaining[idx + 1]
        del remaining[idx:idx + 2]
        with Session(engine) as session:
            patient = session.exec(select(Patient).where(Patient.name == name)).first()
        if patient is None or patient.id is None:
            print(f"Error: no patient named '{name}' found in the database.")
            sys.exit(1)
        return patient.id, remaining

    return 1, remaining


def main() -> None:
    patient_id, remaining_args = resolve_patient_id(sys.argv[1:])
    logger.info(f"Initialising Guardian Phase 0 (patient_id={patient_id}, text mode, OpenAI)…")
    agent = GuardianAgent(patient_id=patient_id)
    # Replace sys.argv so the rest of main() sees only non-flag args.
    sys.argv = [sys.argv[0], *remaining_args]

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
