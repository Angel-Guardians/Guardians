# Guardian — Team To-Do Board

**Branch in flight:** `merge/reconciled-main` (get this onto `main` first, then everyone branches off `main`) · **Repo:** github.com/Angel-Guardians/Guardians

The repo runs end-to-end now: 6-agent LangGraph brain, `/turn`, live SSE feed, `/vitals` ingest+read, Next.js UI. Your job is to swap your real piece in behind its contract without breaking the run. Tick each box as you finish (`- [ ]` → `- [x]`).

---

## Kickoff — all together, ~20 min, do this first

- [ ] Walk the repo: `README.md`, `MERGE_NOTES.md` (what came from which branch), `EXTENDING.md` (how to add a tool/agent/persona)
- [ ] Run it: `pip install -e .`, `guardian-backend`, then the Next.js frontend; hit `GET /health` and send one `/turn`
- [ ] Freeze the contracts out loud — event shape (`backend/events/types.py`), `/turn` + `/vitals` payloads, the LLM `.env` seam. Don't change these alone.
- [ ] Arian shares the Spark `LLM_BASE_URL` the moment the local model answers — **this unblocks everyone's real-model testing**

---

## Arian — Inference, DGX Spark & agent brain

You've got the systems/inference background and already own the Spark. Deliver a reachable local model early; it unblocks real-model testing for the whole team.

**DGX Spark + inference seam** (`SETUP_DGX_SPARK.md`, `backend/llm/`)
- [ ] Stand up the local model endpoint on the Spark; confirm a raw completion returns text
- [ ] Point `.env` at Spark (`LLM_BASE_URL`, `LLM_MODEL`) and confirm a full `/turn` completes with no code changes
- [ ] Share the base URL with the team
- [ ] Verify the provider-neutral seam: same code path works on OpenAI and Spark (this is the core "runs anywhere" story)

**Agent brain** (with Setareh — `backend/agents/`)
- [ ] Pair on hardening the router + system prompts so findings read well on the local model
- [ ] Tune mock/fallback replies so the demo survives a brief model hiccup

**Retrieval / RAG** (`backend/tools/memory.py`, `backend/memory/vector_store.py`)
- [ ] Add a real vector store (pgvector or FAISS) over `data/personas/*.md`, keep the keyword fallback
- [ ] Confirm `recall_history` returns relevant chunks and degrades gracefully with no DB

**Spark proof for the demo**
- [ ] Capture GPU utilization (`nvidia-smi dmon`), model name, tokens/sec, and a network-off → still-works clip

---

## Setareh — Agent brain & orchestration

You own the brain. Goal: each specialist is genuinely useful and the hero arc routes cleanly. Danial pairs with you on the backend pieces.

**Prompt organization** (with Arian — `backend/agents/prompts/`)
- [ ] Extract the six inline `SYSTEM_PROMPT` strings into a `prompts/` folder
- [ ] Pull the duplicated patient/persona block into one shared `PATIENT_CONTEXT` composed into each prompt
- [ ] Add a small config map (agent → active prompt version) for easy A/B without touching agent code
- [ ] Point each agent's `system_prompt` at the registry instead of an inline string

**System prompts** (`backend/agents/*.py`)
- [ ] Tighten `safety` — in-scope, urgent voice, escalates correctly
- [ ] Tighten `health`, `reminder`, `companion`
- [ ] Tighten `behavior`, `caregiver_liaison`

**Router** (`backend/agents/guardian.py`)
- [ ] Keep the deterministic `_SAFETY_KEYWORDS` fast-path intact
- [ ] Reduce misroutes on ambiguous messages
- [ ] Grow `tests/unit/test_router.py` to ≥10 cases, all green

**Tools → real data** (`backend/tools/*.py`, `backend/db/`)
- [ ] `get_schedule` / `mark_med_taken` read+write real rows
- [ ] `log_vital` / `get_medications` hit the DB
- [ ] Confirm the consent/escalation branch demos cleanly both ways (notify family vs. call 911)

---

## Danial — Frontend UI + backend glue

You're across the UI and backend, and helping Setareh. Get the Live page telling the story; build the backend endpoints the UI needs.

**Live page** (`frontend/src/app/live/page.tsx`, `hooks/useEventStream.ts`)
- [ ] Render SSE timeline: transcript → routing → tool calls → reply, color-coded by agent
- [ ] Auto-scroll / handle reconnect on the EventSource

**Vitals chart** (`frontend/src/app/vitals/page.tsx`)
- [ ] Wire `getVitals` into a live-updating chart (heart rate first)

**Reminders + med confirm** (`frontend/src/app/reminders/page.tsx`)
- [ ] List meds + tap-to-confirm intake
- [ ] Backend (with Setareh): land `GET /medications` and `POST /events` (confirm intake) — both are marked TODO in `api.ts`

**Profile editor** (`components/profile/profile-editor.tsx`)
- [ ] Save through `updatePatientProfile`, edits persist across reload

**Vitals pipeline / dev data** (`scripts/inject_vital.py` — stubbed)
- [ ] Implement the simulator so the chart has realistic HR without hardware

---

## Sahar — Scope, data, scenarios & demo

You're driving scope, the data, and demo prep. Goal: honest data + a scripted demo that lands the three hero moments.

**Data** (`data/`)
- [ ] Verify the Toronto cool-spaces dataset is current/clean (CKAN `open.toronto.ca`); if not clean fast, the curated `cool_spaces.json` in the repo is the honest fallback — don't over-search
- [ ] Confirm the nearest cool space is believable for the persona's area
- [ ] Keep the source-citation string honest ("Toronto Heat Relief Network")
- [ ] Sanity-check `data/personas/eleanor.md` reads well as RAG context

**Scenarios & demo script** (`scenarios/`, `tests/scenarios/`)
- [ ] Implement `scripts/demo_reset.py` (stubbed) to reset the DB to a clean demo state
- [ ] Script the fall scenario
- [ ] Script the heat-risk scenario
- [ ] Script the med-reminder scenario

**Demo capture**
- [ ] Record the hero clip once everything's green, plus a fallback clip in case of a live glitch
- [ ] Confirm `pytest -q` is green (smoke, router, scenario-01) so the build is provably working

---

## Mehrazin — Coordinator & integration

- [ ] Merge `merge/reconciled-main` → `main` via PR (reviewers read `MERGE_NOTES.md`) so everyone branches off a clean base
- [ ] Run the kickoff; lock the hero script; freeze the contracts
- [ ] Checkpoint 1 (midday): does it run end-to-end for everyone? Integrate branches.
- [ ] Checkpoint 2 (evening): does it run on the real Spark model + real data? Integrate, then freeze features.
- [ ] Own the handoffs: Spark URL (Arian → all), meds/events endpoints (Setareh ↔ Danial), RAG vector store (Arian ↔ Setareh)
- [ ] Hold scope — anything not serving the hero flow goes to the stretch list
- [ ] Help Sahar with demo + video prep — storyboard the hero flow, narrate/record the clip
- [ ] Write the README submission blurb + the "simulated sensors" honesty section

---

## Frozen by design / cut order

- **Frozen (don't unfreeze unless the demo needs voice):** STT (Whisper), TTS (Kokoro), wakeword, the always-on capture loop, the Wear OS watch app
- **If behind, cut in this order:** behavior/companion extras → real TTS (use browser default) → real RAG (keyword fallback is fine) → drop to the simplest backup scenario
- **Never cut:** the one hero flow · honest Toronto data · the local-Spark proof · the recorded clip
