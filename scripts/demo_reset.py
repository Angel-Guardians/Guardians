"""Reset state for a clean repeatable demo.

Wipes today's Event Log + Incident rows for the demo patient. Re-seeds
the medication schedule so a reminder fires at "demo time + 2 min".
"""
from __future__ import annotations


def main() -> None:
    # TODO:
    #   - delete EventLogEntry where ts >= today
    #   - delete Incident where opened_at >= today
    #   - re-seed Medication.schedule_cron to fire shortly
    raise NotImplementedError


if __name__ == "__main__":
    main()
