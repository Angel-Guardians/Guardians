"""Event bus + Event Pydantic types.

Every signal in Guardian is an Event on this bus. The Orchestrator
subscribes; sub-agents subscribe; the UI subscribes via SSE. See
ARCHITECTURE.md sec. 3.2.
"""
