# Guardian — Team To-Do Board

**Lead / PM:** Mehrazin · **Branch in flight:** `merge/reconciled-main` · **Repo:** github.com/Angel-Guardians/Guardians

Tick each box as you finish it (`- [ ]` → `- [x]`). Assignments are a starting suggestion — reshuffle by strength. Every track can start now; nothing is gated.

---

## Setup — everyone does this once

- [ ] Pull `main` after the reconciled base is merged, branch off it: `git checkout -b feat/<track>-<thing>`
- [ ] Copy `.env.example` → `.env`, fill in `LLM_API_KEY` (OpenAI for now)
- [ ] Confirm local run: `pip install -e .` then `guardian-backend`, hit `GET /health`
- [ ] Read `EXTENDING.md` before adding any tool/agent/persona/scenario
- [ ] Run `python3 -m compileall backend` and `pytest -q` before every push

---

## Setareh — Agent brain & memory/RAG

**Harden the six system prompts** (`backend/agents/*.py`)
- [ ] Tighten `safety` prompt — stays in-scope, urgent voice, escalates correctly
- [ ] Tighten `health`, `reminder`, `companion` prompts
- [ ] Tighten `behavior`, `caregiver_liaison` prompts
- [ ] Add one hand-written scenario per agent under `tests/scenarios/`

**Improve the router** (`backend/agents/guardian.py`)
- [ ] Keep the deterministic `_SAFETY_KEYWORDS` fast-path intact
- [ ] Reduce misroutes on ambiguous messages
- [ ] Grow `tests/unit/test_router.py` to ≥10 cases, all green

**Real RAG over persona history**
- [ ] Add `backend/memory/vector_store.py` (pgvector path)
- [ ] Make `memory.py` use pgvector when `MEMORY_BACKEND=pgvector`, keyword fallback otherwise
- [ ] Verify `recall_history` returns relevant chunks from `data/personas/eleanor.md`
- [ ] Confirm graceful degrade with no DB present

**Wire tool stubs to the DB** (`backend/tools/*.py`, `backend/db/`)
- [ ] `get_schedule` / `mark_med_taken` read+write real rows
- [ ] `log_vital` / `get_medications` hit the DB
- [ ] One reminder turn round-trips through a real schedule row

---

## Arian — Frontend (Next.js)

**Live page** (`frontend/src/app/live/page.tsx`, `hooks/useEventStream.ts`)
- [ ] Render SSE timeline: transcript → routing → tool calls → reply
- [ ] Color-code each step by agent
- [ ] Auto-scroll / handle reconnect on the EventSource

**Vitals chart** (`frontend/src/app/vitals/page.tsx`)
- [ ] Wire `getVitals` into a chart (heart rate first)
- [ ] Live-update as new points arrive

**Reminders + med confirm** (`frontend/src/app/reminders/page.tsx`)
- [ ] List meds (mock data until backend endpoints land — coordinate w/ Setareh)
- [ ] Tap-to-confirm intake via `confirmIntake`
- [ ] Swap mock → real once `listMedications` ships

**Profile editor** (`components/profile/profile-editor.tsx`)
- [ ] Save through `updatePatientProfile`
- [ ] Edits persist across reload

---

## Danial — Watch, vitals pipeline & always-on sensing

**Vitals simulator first** (`scripts/inject_vital.py` — currently stubbed)
- [ ] Implement it to stream synthetic HR into the DB
- [ ] Confirm points show via `GET /vitals` (this unblocks Arian's chart)

**Wear OS app → backend** (`watch/app/`)
- [ ] Post HR every 60s to `POST /vitals/ingest`
- [ ] Match contract `{patient_id, device, readings:[{kind,value,ts}]}`
- [ ] Confirm rows land and render in the UI

**Always-on capture seam** (`backend/always_on/capture.py`, `runner.py` — stubbed)
- [ ] Make the path importable and run as a clean no-op (STT/wakeword stay frozen)
- [ ] Leave clear `TODO` markers where Whisper/wakeword plug in

**Stretch**
- [ ] Real Polar H10 chest-strap HR via `POLAR_H10_MAC`

---

## Sahar — Infra, DGX Spark, observability, scenarios & tests

**DGX Spark deployment** (`SETUP_DGX_SPARK.md`)
- [ ] Stand up the local model endpoint
- [ ] Point `.env` at Spark, confirm a turn completes (no code changes)
- [ ] Document any gaps back into `SETUP_DGX_SPARK.md`

**LangSmith observability**
- [ ] Set `LANGSMITH_TRACING=true` + key
- [ ] Confirm one span per node, tool calls nested
- [ ] Capture a screenshot for the demo

**Scenarios & demo script** (`scenarios/`, `tests/scenarios/`)
- [ ] Implement `scripts/demo_reset.py` (stubbed) to reset DB to clean demo state
- [ ] Script the fall scenario
- [ ] Script the heat-risk scenario
- [ ] Script the med-reminder scenario

**pgvector + docker-compose** (`docker-compose.yml`)
- [ ] Bring up `pgvector/pgvector:pg17`
- [ ] Point `DATABASE_URL` at it, confirm seed/migrations
- [ ] Hand off to Setareh for RAG

**Tests**
- [ ] Smoke + router + scenario-01 green
- [ ] `pytest -q` passes locally / CI, covers each agent route

---

## Mehrazin (you) — Lead / PM

- [ ] Merge `merge/reconciled-main` → `main` via PR (point reviewers at `MERGE_NOTES.md`)
- [ ] Own handoffs: reminders/meds (Setareh↔Arian), vitals contract (Danial↔Arian), pgvector (Setareh↔Sahar)
- [ ] Protect demo time — Live page + traces are the showpiece
- [ ] Daily 10-min standup against this board

---

## Handoffs to watch

- Reminders/meds endpoints: **Setareh → Arian**
- Vitals simulator data: **Danial → Arian**
- pgvector DB: **Sahar → Setareh**
- Frozen by design (don't unfreeze unless demo needs voice): STT (Whisper), TTS (Kokoro), wakeword