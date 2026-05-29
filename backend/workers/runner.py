"""Entrypoint for the workers process group.

  $ guardian-workers

Starts Arq workers. Each worker subscribes to the same Redis Arq queue
and runs scheduled jobs (baseline updates, weekly summaries, behavior
longitudinal checks).
"""
from __future__ import annotations


def run() -> None:
    """CLI entry. Loads ArqWorkerSettings and runs the Arq worker."""
    # TODO: from arq import run_worker; run_worker(WorkerSettings)
    raise NotImplementedError


if __name__ == "__main__":
    run()
