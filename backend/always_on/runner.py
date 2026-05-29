"""Entrypoint for the always-on process group.

  $ guardian-always-on

Pins this process to the always-on CPU core range (.env
ALWAYS_ON_CPU_CORES), starts the mic + wake + VAD + STT pipeline plus
the wearable / env sensor pollers, and publishes candidate events to
the backend process over a local TCP socket (or NATS in production).
"""
from __future__ import annotations

import asyncio


async def _main() -> None:
    """Start every always-on producer."""
    # TODO:
    #   - taskset / sched_setaffinity to pin to settings.always_on_cpu_cores
    #   - start AudioPipeline (capture -> wake -> VAD -> STT -> emit)
    #   - start WearablePoller (Polar H10 BLE -> emit VitalSampleEvent)
    #   - start EnvSensorPoller -> emit EnvSignalEvent
    #   - start AudioEventClassifier (YAMNet -> emit AudioEventDetectedEvent)
    raise NotImplementedError


def run() -> None:
    """CLI entry."""
    asyncio.run(_main())


if __name__ == "__main__":
    run()
