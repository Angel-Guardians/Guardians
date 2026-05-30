# Onboarding — read this first

New to the repo? Start here. This is a map to the docs that already exist plus a
per-person path so you only read what's relevant to your track. Don't duplicate
code — if you find yourself copy-pasting, there's probably a shared place for it
(see "Golden rules" below).

---

## Everyone — the 30-minute shared path

Read these four, in order, then run it once. Total ~30 min.

1. **`README.md`** — what Guardian is, the one-paragraph architecture diagram, and
   the run-now commands. Start here.
2. **`MERGE_NOTES.md`** — this `main` is a reconciliation of three branches. This
   tells you what came from where, so you know which code is battle-tested vs. glue.
3. **`CODEBASE_MAP.md`** — where everything lives (tour of `backend/`, `frontend/`,
   `watch/`). Skim; you'll come back to it.
4. **`EXTENDING.md`** — the four safe extension points (add a tool / agent / prompt
   / persona / scenario). Read before you write anything.

Then **run it** (from `README.md`): `cp .env.example .env` (add your `LLM_API_KEY`),
`pip install -e ".[dev]"`, `guardian-backend`, and `python scripts/phase0.py` to talk
to it. Seeing one full turn end-to-end is worth more than reading another doc.

Optional deeper context: **`ARCHITECTURE.md`** (the *why* behind the design) and
**`HACKATHON_3DAY_PLAN.md`** (build order). Long — read only if you want the full picture.

Your task list lives in **`TEAM_TASKS.md`** (or open `TEAM_TASKS.html` for clickable
tick boxes).

### Golden rules
- **No duplication.** Edit shared things in one place: patient details →
  `backend/agents/prompts/_base.py`; data contracts → `backend/events/types.py` and
  the `/turn` + `/vitals` payloads. If you copy a block to a second file, stop and
  ask where the shared home is.
- **Branch off `main`**, work in your own files, small PRs, tag Mehrazin.
- **Don't break the run.** `python -m compileall backend` and `pytest -q` before pushing.
- The conversational path does **not** depend on `always_on/`, `orchestrator/`, or
  `workers/` — those are scaffolds (`NotImplementedError`). Ignore them unless your
  task says otherwise.

---

## Arian — inference, DGX Spark & agent brain

Read after the shared path:
- **`SETUP_DGX_SPARK.md`** — your primary doc: stand up the local model, point `.env`.
- **`MODELS.md`** — what we run now (one model behind the seam) and exactly which
  Nemotron model to switch to, with effort estimates. Read before you pick a model.
- **`backend/llm/`** — the provider-neutral seam. `config.py` (env → settings),
  `factory.py` (`build_llm`), `openai_compatible.py` (the only file importing `openai`).
  This is what makes "OpenAI now, Spark later" a one-env-var change.
- **`backend/agents/base.py`** (the tool-calling loop) and **`backend/agents/guardian.py`**
  (the hybrid router) — for the agent-brain work you share with Setareh.
- **`backend/tools/memory.py`** — the RAG entry point you'll back with a vector store.
- `.env.example` — the `LLM_*` block you'll be flipping.

First win: a reachable Spark endpoint + shared `LLM_BASE_URL`. It unblocks everyone.

## Setareh — agent brain & orchestration

Read after the shared path:
- **`backend/agents/prompts/`** — prompts now live here (not inline). Edit wording in
  the per-agent file; edit Eleanor's shared details in `_base.py`; select A/B
  versions in `active.toml`. See `EXTENDING.md` → "Edit a prompt".
- **`backend/agents/guardian.py`** — the router (`_SAFETY_KEYWORDS` fast-path +
  `_ROUTER_PROMPT`) and the per-turn flow.
- **`backend/agents/graph.py`** — the LangGraph wiring (router → 6 specialists).
- **`backend/agents/base.py`** — the tool-calling loop every specialist inherits.
- **`backend/tools/*.py`** + **`backend/db/`** — for wiring tool stubs to real rows.
- **`tests/unit/test_router.py`** — extend this as you tune routing.

## Danial — frontend UI + backend glue

Read after the shared path:
- **`frontend/src/lib/api.ts`** — the typed client; shows every endpoint and which
  are still `TODO(backend)` (medications, confirm-intake).
- **`frontend/src/hooks/useEventStream.ts`** — the SSE consumer; expects
  `{id, kind, ts, summary, payload}`.
- **`frontend/src/app/{live,vitals,reminders,profile}/page.tsx`** — your pages.
- **`backend/api/turn.py`**, **`events_sse.py`**, **`vitals.py`** — the endpoints
  feeding the UI; read these so the contract is clear when you add meds/events.
- **`frontend/AGENTS.md`** / **`frontend/CLAUDE.md`** — frontend conventions.

## Sahar — scope, data, scenarios & demo

Read after the shared path:
- **`data/README.md`** + **`data/cool_spaces.json`** + **`data/personas/eleanor.md`** —
  the data shape and the curated fallback dataset.
- **`backend/tools/civic.py`** — how the cool-space lookup uses your data.
- **`scenarios/`** + **`tests/scenarios/`** — the scripted demo beats.
- **`scripts/demo_reset.py`** (stubbed — you implement) and **`scripts/try_live.py`**
  (scripted inputs) — your demo-driving scripts.
- **`tests/test_smoke.py`** — the green-build gate.

## Mehrazin — coordinator

- **`MERGE_NOTES.md`** for the PR description; **`backend/events/types.py`**
  for the contracts to freeze; **`TEAM_TASKS.md`** for the board and checkpoints.
