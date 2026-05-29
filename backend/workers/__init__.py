"""Slow-time path - Arq background workers.

Nightly / weekly / monthly jobs that read the Event Log and emit
synthetic events (anomalies, pattern absences, baseline updates).

  baseline_updater.py    - nightly: refresh per-user baselines
  weekly_summary.py      - Sunday eve: compress a week into a recap
  behavior_nightly.py    - nightly: run Behavior longitudinal checks
"""
