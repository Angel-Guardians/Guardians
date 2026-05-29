"""Shared pytest fixtures.

Reusable across unit + scenario tests:
  - in-memory SQLite database
  - mocked event bus
  - seeded Eleanor profile
  - fake LLM that echoes a canned response
  - fake TTS that records utterances instead of speaking
"""
from __future__ import annotations

import pytest


@pytest.fixture
def db_session():
    """In-memory SQLite session for tests."""
    # TODO: from sqlmodel import Session, SQLModel; create in-memory engine
    raise NotImplementedError


@pytest.fixture
def event_bus():
    """Fresh EventBus per test."""
    from backend.events.bus import EventBus

    return EventBus()


@pytest.fixture
def eleanor(db_session):
    """Seeded Eleanor (70, cardiac, lives alone) for scenario tests."""
    # TODO: insert Patient + EmergencyContact rows
    raise NotImplementedError
