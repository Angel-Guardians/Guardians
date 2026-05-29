"""Unit tests for the hybrid router."""
from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Day 1 PM target")
async def test_fall_sound_routes_to_safety() -> None:
    raise NotImplementedError


@pytest.mark.skip(reason="Day 2 AM target")
async def test_scheduled_reminder_routes_to_reminder() -> None:
    raise NotImplementedError


@pytest.mark.skip(reason="Day 2 AM target")
async def test_ambiguous_utterance_falls_through_to_llm() -> None:
    raise NotImplementedError
