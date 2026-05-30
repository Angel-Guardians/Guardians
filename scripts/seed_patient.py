"""Seed demo patients into the database.

Eleanor (70), Margaret (64), Sarah (30) - the three personas the demo
scenarios assume. Idempotent: safe to re-run.

  $ guardian-seed
"""
from __future__ import annotations

from backend.db.seed import seed_all


def main() -> None:
    seed_all()
    print("Seed complete.")


if __name__ == "__main__":
    main()
