"""Seed demo patients into the database.

Eleanor (70), Margaret (64), Sarah (30) - the three personas the demo
scenarios assume. Idempotent: safe to re-run.

  $ guardian-seed
"""
from __future__ import annotations


def main() -> None:
    """Populate Patient + EmergencyContact + Medication + ConsentMatrix."""
    # TODO:
    #   - open a session
    #   - upsert Eleanor (cardiac history, daughter Maria as primary contact)
    #   - upsert Margaret (hypertension, T2 diabetes, complex med regimen)
    #   - upsert Sarah (healthy, iron-deficient, workout-day logic)
    #   - default ConsentMatrix entries for each
    raise NotImplementedError


if __name__ == "__main__":
    main()
