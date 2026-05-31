# Guardian — Build Session Summary (for evaluation)

## Project context
Guardian is a local-first, multi-agent personal-safety/wellbeing assistant for vulnerable people (hero use case: an isolated 78-year-old, Margaret, during a Toronto heat warning). It's a hackathon project (Spark Hack Series, Toronto; sponsors NVIDIA/ASUS/Antler) that must run an agentic system on an **NVIDIA DGX Spark** using **Toronto Open Data**. Constraints: effectively one build day, a 5-person team with mixed roles, and the scored deliverable is a 3–5 min demo video plus a skimmable repo. The rubric weights Technical Execution (30), NVIDIA Ecosystem/Spark utility (30), Value/Impact (20), Innovation (20).

This session produced two things: (1) a set of strategic/architectural decisions, and (2) a complete, ready-to-commit code repository implementing them.

## Key decisions made (and rationale)
- **Model: NVIDIA Nemotron-3** served via **Ollama's OpenAI-compatible endpoint** on the Spark (primary `nemotron-3-nano:30b`, stretch `nemotron-3-super:120b`). Chosen over alternatives because the organizers named Nemotron specifically and NVIDIA's own Spark reference path (the NemoClaw playbook) defaults to Ollama. SGLang/vLLM/TensorRT were deliberately deprioritized to an optional "upgrade lane" behind the same endpoint, since their throughput advantage is irrelevant for a single-user demo.
- **Architecture principle = contracts, not coupling.** Every team boundary is a frozen schema; the LLM, data layer, sensors, and voice each swap at one config line or file. This is what lets 4 people work in parallel and lets the whole system run on a fresh clone in mock mode before any real component is wired in.
- **Reliability principle = deterministic control flow + LLM for language only.** Risk scoring, routing, and consent logic are deterministic Python; the local model is used only for natural-language outputs (agent findings and the spoken response). The demo therefore can't crash on a flaky/absent model, while still genuinely running local inference for everything shown.
- **Voice:** TTS output is included as the emotional core; the agent *chooses* its tone via a `voice_style` field (the novel agentic beat). Emotion *detection* is simulated metadata, not a real model. Pipeline (STT→text agent→TTS), not a unified multimodal model. Browser Web Speech API as the floor; NVIDIA NeMo/Riva TTS as a stretch.
- **Simulation is first-class and honest:** a clearly-labeled "Sensor Simulator (stands in for hardware)" UI zone, visually fenced from the real Guardian decision UI. The separation *is* the honesty story.
- **Scope discipline:** one hero scenario done well, with a backup scenario that needs no civic data.

## What was built — the repository (30 files, ~260 KB)
Stack chosen for zero-build reliability: **FastAPI backend that also serves a vanilla HTML/CSS/JS frontend** (no node/build step), with **stdlib-only LLM HTTP calls** (no extra deps on the LLM path). Core dependencies are just `fastapi` + `uvicorn`.

Backend (`backend/`):
- `schemas.py` — the frozen Pydantic contracts (Event, AgentResponse, OrchestratorDecision, AgentActivity, ToolCall, SpokenResponse, RecommendedAction, InferenceMeta, CoolSpace). Permissive (extra fields allowed).
- `orchestrator.py` — running Context state, `assess_risk` (LOW/MEDIUM/HIGH/CRITICAL scoring), `route`, `choose_voice_style`, `consent_action`, and `handle_event`. A positive tap clears distress and de-escalates; no response → unresponsive → CRITICAL → 911.
- `agents.py` — 5 sub-agent personas (health/safety/behavior/companion/caregiver) = same model, different system prompts.
- `tools.py` — `find_nearest_open_cool_space` (real, geo-distance) plus stubs (`notify_caregiver`, `speak`, `log_event`) returning valid shapes.
- `rag.py` — haversine geo-lookup that works with no dependencies, plus a keyword `semantic_search` with a FAISS upgrade path behind the same signature.
- `llm.py` — `chat()` adapter: real OpenAI-compatible call via stdlib `urllib` (works for Ollama/vLLM/SGLang) + a smart per-agent mock fallback; "auto" mode probes the endpoint and degrades gracefully; tracks tokens/sec and active mode.
- `simulator.py`, `event_log.py`, `main.py` (FastAPI REST + WebSocket; serves frontend; streams scenario replay).

Frontend (`frontend/`): `index.html` + `styles.css` + `app.js` — two-zone UI (fenced simulator vs. Guardian decision view: persona, risk badge, streaming agent activity, cool-space card with data source, speech box with browser TTS keyed to `voice_style`, caregiver-draft action card, audit log, Spark badge). Calm "control-room" aesthetic, WebSocket-driven, no build step.

Data/scenarios: `data/cool_spaces.json` (20 curated real Toronto Heat Relief Network locations as the honest fallback), `data/personas.json`, `scenarios/heat_warning_margaret.json` (hero), `scenarios/silent_morning.json` (backup).

Docs + infra: `README.md`, `CONTRACTS.md`, `TODO.md` (per-person checklist with test gates and 3 integration checkpoints), `SCENARIOS.md` (beat-by-beat walkthroughs with expected risk per tick), `tests/test_smoke.py` (the merge gate), `requirements.txt`, `run.sh`, `Dockerfile`, `docker-compose.yml`, `.gitignore`, plus per-folder READMEs.

## Verification performed
- All 12 Python files compile (`py_compile`); all 4 JSON files are valid; `app.js` passes `node -c`.
- The orchestrator logic was run end-to-end via a minimal `pydantic` stub (sandbox had no network to `pip install`). Confirmed:
  - Hero arc per tick: LOW → LOW → MEDIUM → HIGH → CRITICAL (distress) → HIGH (taps okay → calm voice → notify daughter under family-first consent).
  - Branch (no response) → CRITICAL → call_emergency → 911.
  - Geo lookup returns nearest *accessible* cool space (519 Community Centre, 0.21 km), correctly sorted and filtered.
  - Backup scenario → HIGH → notify_caregiver.
  - `tests/test_smoke.py` prints "smoke test passed."

## Known limitations / what an evaluator should re-check
- **Not run live:** because the sandbox had no network, I could not `pip install fastapi/uvicorn/pydantic`, so the **FastAPI server, the WebSocket streaming, and the browser frontend were not executed**. Logic was verified through a Pydantic stub; the web layer is standard but unproven at runtime. First real-environment step should be `./run.sh` then open `http://localhost:8000`.
- **No test against a real Nemotron endpoint** was possible here; the `llm.py` real path is written to spec but unverified against an actual Ollama/Spark instance.
- **Toronto cool-spaces data is curated, not live-pulled.** The CKAN package was mid-migration; the repo ships a curated fallback and documents the live-refresh procedure, with a "verify before 10am or use fallback" rule.
- The "open now" check in `rag.py` is intentionally naive (treats listed spaces as open); flagged in code as an upgrade.
- Web Speech API TTS quality/voice availability varies by browser (tested target is Chrome).

## Deliverable
A single zip, `guardian.zip`, containing the full repo — designed to be committed to `main` as-is, run immediately in mock mode, then pointed at the Spark via `GUARDIAN_LLM_BASE_URL` / `GUARDIAN_USE_MOCK_LLM=0`.
