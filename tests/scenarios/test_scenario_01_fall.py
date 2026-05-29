"""Scenario 1 - Midnight fall (Eleanor).

Inject: AudioEventDetectedEvent(fall_sound) + VitalSampleEvent(hr=138).
Assert:
  - Safety Agent invokes emergency_caller with Eleanor's profile in summary
  - Companion Agent invokes tts with reassurance
  - Event Log contains an Incident row with peak_severity=CALL
  - CaregiverLiaison invokes fhir_share after EMS marker
"""
from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Day 1 PM target")
async def test_scenario_01_fall_e2e(eleanor, event_bus) -> None:
    # TODO: implement after Day 1 PM
    raise NotImplementedError
