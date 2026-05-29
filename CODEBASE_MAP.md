# Guardian - Codebase Map

Quick navigation for the repo. For *why* the architecture looks like this, read [`ARCHITECTURE.md`](ARCHITECTURE.md). For the build order, read [`HACKATHON_3DAY_PLAN.md`](HACKATHON_3DAY_PLAN.md).

```
guardian/
├── backend/                    # Single Python package, one FastAPI process
│   ├── main.py                 # Uvicorn entry; wires routers + lifespan
│   ├── config.py               # Settings via pydantic-settings (.env)
│   ├── logging.py              # Loguru config
│   │
│   ├── always_on/              # CPU-pinned background services (Grace cores)
│   │   ├── runner.py           # Entrypoint; starts mic+wake+VAD+STT loop
│   │   └── capture.py          # The always-on audio pipeline
│   │   # Filled later: vad.py, transcribe.py, wake.py, audio_events.py,
│   │   # wearable.py, env_sensors.py
│   │
│   ├── orchestrator/           # Tier 1 - the supervisor
│   │   ├── supervisor.py       # LangGraph Supervisor
│   │   ├── router.py           # Hybrid rule+LLM router
│   │   └── risk_classifier.py  # CTAS-aligned Tier 1-4 classifier
│   │
│   ├── agents/                 # Tier 2 - the six sub-agents
│   │   ├── base.py             # SubAgent abstract base
│   │   ├── llm.py              # Ollama wrapper
│   │   ├── voice_profiles.py   # Enum of voice profiles per sub-agent
│   │   ├── safety.py           # Falls, panic, violence - can call 911
│   │   ├── health.py           # Vitals, anomalies, chronic
│   │   ├── reminder.py         # Meds, vitamins, appointments
│   │   ├── companion.py        # Talk, calm, recall
│   │   ├── behavior.py         # Long-horizon behavioural monitoring
│   │   └── caregiver_liaison.py # Outbound to humans (doctors, family, court)
│   │
│   ├── tools/                  # Tier 3 - the shared tool bus
│   │   ├── decorators.py       # @audit_log, @idempotent, @consent_check
│   │   ├── registry.py         # Tool registration + lookup
│   │   ├── sensing/            # Audio listener, wearable, env, geo, manual
│   │   ├── memory_reasoning/   # Event log, baselines, anomalies, RAG, KB
│   │   ├── action/             # TTS, notifications, 911, contact-tree, UI
│   │   └── integrations/       # Fitbit, Dexcom, Calendar, Twilio, FHIR, MCP
│   │
│   ├── api/                    # FastAPI routers
│   │   ├── patient.py          # Profile CRUD
│   │   └── events_sse.py       # /events/sse for the UI
│   │
│   ├── services/               # Business logic shared with agents
│   │   # patient_profile.py, incident_recorder.py, reminder_scheduler.py,
│   │   # emergency_dispatch.py, consent_check.py
│   │
│   ├── db/                     # SQLModel + Alembic
│   │   ├── session.py
│   │   └── models.py           # Patient, Incident, EventLogEntry, ...
│   │
│   ├── events/                 # The event bus + Event Pydantic types
│   │   ├── bus.py
│   │   └── types.py
│   │
│   └── workers/                # Arq workers (slow-time path)
│       └── runner.py
│
├── ui/                         # Streamlit (hackathon); Next.js (production)
│   ├── app.py                  # Streamlit entry
│   └── pages/                  # Multi-page Streamlit app
│
├── scripts/                    # One-shot CLI helpers
│   ├── seed_patient.py         # Seed Eleanor + Margaret + Sarah profiles
│   └── demo_reset.py           # Reset state for repeatable demos
│
├── tests/
│   ├── conftest.py
│   └── scenarios/              # One test per demo scenario (1..27)
│
├── README.md                   # Project pitch
├── ARCHITECTURE.md             # The definitive architecture doc
├── TECH_STACK.md               # Per-layer module picks
├── guardian_scenarios.md       # 27 scenario playbooks
├── DEVELOPMENT_PLAN.md         # Long-term phased roadmap
├── HACKATHON_3DAY_PLAN.md      # 72-hour build plan
├── CODEBASE_MAP.md             # (this file)
├── pyproject.toml
├── Makefile
├── .env.example
└── .gitignore
```

## Where to put new code

| You're adding... | Goes in |
|---|---|
| A new sub-agent | `backend/agents/<name>.py`, register in `backend/agents/__init__.py` |
| A new tool | The right bucket under `backend/tools/<bucket>/<tool>.py`, register via `@register_tool` |
| A new always-on signal source | `backend/always_on/<source>.py`, emit events via the bus |
| A new event type | `backend/events/types.py` (one Pydantic model per event) |
| A new DB table | `backend/db/models.py`, then `alembic revision --autogenerate` |
| A new external API integration | `backend/tools/integrations/<service>.py` |
| A new UI page | `ui/pages/<N>_<Name>.py` |
| A new test scenario | `tests/scenarios/test_scenario_<NN>_<name>.py` |
| A new background job | `backend/workers/<job>.py`, register in `backend/workers/runner.py` |

## The three running processes

In production we run **three Python processes** on the DGX:

1. **`guardian-always-on`** - CPU-pinned to cores 0-5. Mic, wake-word, VAD, STT-lite, audio events, wearable, env sensors. Publishes candidate events to the bus.
2. **`guardian-backend`** - The FastAPI + Orchestrator + Sub-Agents + Tools process. Binds the LLM to the GPU. Subscribes to the bus.
3. **`guardian-workers`** - Arq workers for slow-time jobs (nightly baselines, weekly summaries, behavior trends).

During hackathon Phase 1, these can run as a single process (the always-on and worker code lives in the same Python module). The split formalises in Phase 6.
