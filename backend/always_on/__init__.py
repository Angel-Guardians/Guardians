"""Always-on tier.

CPU-pinned background services: wake word, VAD, STT-lite, audio event
classification, wearable BLE ingest, environmental sensor poll,
scheduler. Runs as its own process (`guardian-always-on`).

This package MUST NOT import `langgraph`, `langchain_*`, `torch`, or any
GPU library. Enforced in CI. The always-on tier exists to be cheap and
isolated from LLM crashes.
"""
