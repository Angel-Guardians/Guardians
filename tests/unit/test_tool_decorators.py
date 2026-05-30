"""Unit tests for the cross-cutting tool decorators."""
from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Day 2 AM target")
def test_consent_check_blocks_egress_when_denied() -> None:
    raise NotImplementedError


@pytest.mark.skip(reason="Day 2 AM target")
def test_idempotent_dedupes_within_window() -> None:
    raise NotImplementedError


@pytest.mark.skip(reason="Day 1 PM target")
def test_audit_log_writes_start_and_end() -> None:
    raise NotImplementedError
