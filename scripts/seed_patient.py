"""Seed the demo patient into the database.

Seeds Eleanor (70) — the single canonical persona the scenarios and prompts
assume. Idempotent: safe to re-run.

  $ guardian-seed
"""
from __future__ import annotations

from backend.db.seed import seed_all


def main() -> None:
    seed_all()
    print("Seed complete.")


if __name__ == "__main__":
    main()
