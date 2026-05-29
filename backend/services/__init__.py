"""Business logic shared between the API layer and the sub-agents.

The Backend exposes these as Python modules to the agents (no extra
network hop) and as HTTP/SSE endpoints to the UI. See ARCHITECTURE.md
sec. 2 "Backend".

  patient_profile.py     - read/write Patient + EmergencyContact
  incident_recorder.py   - open / close Incident; attach events to it
  reminder_scheduler.py  - APScheduler wiring
  emergency_dispatch.py  - the side-effect broker (911, family, FHIR)
  consent_check.py       - ConsentMatrix lookups; used by tool decorator
"""
