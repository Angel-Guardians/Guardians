# Merge notes — what came from which branch

This `main` is a reconciliation of three branches: **main** (platform spine),
**setareh** (the working brain), and **watch** (real vitals hardware).

## Survived — and from where

**From `setareh` (the only end-to-end working brain):**
- `backend/llm/` — provider-neutral LLM seam (OpenAI/vLLM/NIM/Ollama via one
  adapter). This is what lets us use OpenAI now and the Spark later.
- `backend/agents/` — `graph.py` (LangGraph router→6 specialists), `guardian.py`
  (hybrid keyword+LLM router), `base.py` (tool-calling loop), and the six
  specialist agents (safety, health, reminder, companion, behavior, caregiver).
- `backend/tools/` — `registry.py` + working stubs (emergency, health, reminder).
- `scripts/phase0.py`, `scripts/try_live.py`, `tests/fakes.py`, the router unit test.
- LangSmith tracing (`backend/llm/tracing.py`), env-gated.

**From `main` (the platform spine):**
- FastAPI app shell, `events/bus.py` (in-proc pub/sub) + `events/types.py`.
- `db/` (SQLModel models, session, seed) and `services/patient_profile.py`,
  `api/patient.py`, `api/schemas.py`.
- The entire **Next.js frontend** (Live / Vitals / Reminders / Profile).
- `docker-compose.yml`, `Makefile`, `ARCHITECTURE.md`, `CODEBASE_MAP.md`.

**From `watch`:**
- The whole `watch/` Wear OS app (real heart-rate/steps/calories, offline buffer,
  60s upload). This replaces "simulated sensors" with real hardware.

**Newly written for the merge (glue + asks):**
- `backend/api/turn.py` — `POST /turn`: runs a turn through the graph and publishes
  utterance/routing/tool/reply events to the bus.
- `backend/api/events_sse.py` — implemented (was a stub) from `bus.stream()`.
- `backend/api/vitals.py` — `POST /vitals/ingest` + `GET /vitals` (watch contract).
- `backend/main.py` — builds `GuardianAgent` at startup, starts the bus, mounts routers.
- `GuardianAgent.turn()` — returns `{route, reply, tool_calls}` for the API/UI.
- `backend/tools/civic.py` (cool-space lookup) + `backend/tools/memory.py`
  (person-history recall) + `data/personas/eleanor.md`.
- Per-agent `voice_profile` / `escalation_ceiling` metadata (merging main's
  `voice_profiles.py` intent into the working agents).
- Reconciled `pyproject.toml`, `.env.example`; SQLite default; pgvector-ready compose.

## Did NOT survive / changed

- **main's brain stubs** — `orchestrator/{router,risk_classifier,supervisor}.py`
  and `agents/llm.py` (Ollama-only) were all `NotImplementedError` or single-provider.
  Replaced by setareh's working LangGraph brain. `agents/llm.py` now raises a clear
  "use backend.llm" error so stale imports fail loudly.
- **setareh's Streamlit UI** (`ui/`) — dropped in favour of main's Next.js frontend.
- **Single hard-coded Ollama provider** — replaced by the env-driven seam.
- **Postgres-only default** — now SQLite by default so it runs with zero infra;
  Postgres/pgvector is the documented RAG upgrade.

## Still stubbed (intentionally, not on the demo path)

`backend/orchestrator/` (event-driven supervisor), `backend/always_on/` (wake word
+ STT), `backend/workers/` (anomaly detection), and `scripts/inject_vital.py` still
raise `NotImplementedError`. The conversational `/turn` path and the watch `/vitals`
path do not import them. They're the next tier to wire onto the same `GuardianAgent`.
STT/TTS are deliberately frozen (see `.env.example` tail).
