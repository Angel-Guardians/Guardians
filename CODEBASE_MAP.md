# Guardian — Codebase Map

Where everything lives in the **merged `main`**. This describes the code that
actually runs today. For the *why* behind the design, see `ARCHITECTURE.md` (note:
that doc is the original vision — parts are aspirational, see its banner).

```
Guardians/
├── backend/                      # One Python package, one FastAPI process
│   ├── main.py                   # Uvicorn entry; wires routers + lifespan
│   ├── config.py                 # App settings via pydantic-settings (.env)
│   │                             #   ⚠ its llm_model_* / whisper_* fields are
│   │                             #   legacy and NOT used by the live path — the
│   │                             #   model is set in backend/llm/. See MODELS.md.
│   ├── logging.py                # Loguru config
│   │
│   ├── llm/                      # ★ Provider-neutral LLM seam (OpenAI now, Spark later)
│   │   ├── config.py             # LLM_* env -> settings (the ONLY model config)
│   │   ├── factory.py            # build_llm()
│   │   ├── openai_compatible.py  # the ONLY file importing `openai`
│   │   ├── base.py               # LLM interface
│   │   └── tracing.py            # optional LangSmith spans (no-op when unset)
│   │
│   ├── agents/                   # The router + six specialists
│   │   ├── guardian.py           # ★ Hybrid router (keyword fast-path + LLM)
│   │   ├── graph.py              # LangGraph wiring (router -> 6 specialists)
│   │   ├── base.py               # ToolCallingAgent — the tool-calling loop
│   │   ├── safety.py  health.py  reminder.py
│   │   ├── companion.py  behavior.py  caregiver_liaison.py
│   │   ├── prompts/              # ★ Prompt registry (no inline prompt strings)
│   │   │   ├── _base.py          #   PATIENT_CONTEXT (Eleanor) — single source
│   │   │   ├── <agent>.py        #   per-agent VERSIONS dict
│   │   │   ├── active.toml       #   which version each agent uses (edit here)
│   │   │   └── __init__.py       #   get_prompt(name)
│   │   ├── llm.py                #   legacy shim — raises a clear error; ignore
│   │   └── voice_profiles.py     #   legacy; voice metadata now lives on agents
│   │
│   ├── tools/                    # Tool registry + stubbed tools
│   │   ├── registry.py           # build_default_registry()
│   │   ├── emergency.py  health.py  reminder.py  civic.py  memory.py
│   │   └── decorators.py         # @audit_log etc.
│   │
│   ├── api/                      # FastAPI routers
│   │   ├── turn.py               # POST /turn  (text in -> route+reply+tool_calls)
│   │   ├── vitals.py             # POST /vitals/ingest, GET /vitals (watch contract)
│   │   ├── events_sse.py         # GET /events/sse  (the Live page feed)
│   │   ├── patient.py            # profile
│   │   └── schemas.py            # request/response models
│   │
│   ├── events/                   # In-process pub/sub bus + event types
│   │   ├── bus.py
│   │   └── types.py              # ★ event contracts — freeze before integration
│   │
│   ├── db/                       # SQLModel models, session, seed (SQLite default)
│   │   ├── models.py  session.py  seed.py
│   │
│   ├── services/                 # patient_profile.py (logic shared with agents)
│   │
│   └── orchestrator/, always_on/, workers/
│       └── ⚠ NOT wired — scaffolds that raise NotImplementedError. The
│         conversational path does not depend on these. Ignore unless your
│         task is the always-on sensor tier. (See EXTENDING.md → "Not yet wired".)
│
├── frontend/                     # Next.js 16 (App Router) + Tailwind + shadcn/ui
│   └── src/
│       ├── app/{live,vitals,reminders,profile}/page.tsx   # the four pages
│       ├── hooks/useEventStream.ts        # SSE consumer ({id,kind,ts,summary,payload})
│       └── lib/api.ts                      # typed client (marks TODO(backend) endpoints)
│
├── data/personas/eleanor.md      # life-history note (RAG source)
├── data/cool_spaces.json         # curated cool-space fallback dataset
│
├── scripts/
│   ├── phase0.py                 # talk to Guardian (text in/out, single process)
│   ├── try_live.py               # 5 scripted inputs through the real model
│   ├── seed_patient.py           # seed Eleanor
│   ├── inject_vital.py  demo_reset.py   # demo helpers (some stubbed)
│
├── tests/
│   ├── test_smoke.py             # green-build gate
│   ├── unit/test_router.py       # routing tests (extend as you tune routing)
│   └── scenarios/                # one test per demo scenario
│
└── docs:  README → ONBOARDING → MERGE_NOTES → (this) → EXTENDING
         MODELS.md (models + Nemotron), SETUP_DGX_SPARK.md, ARCHITECTURE.md*
         (* original vision — read its banner before trusting details)
```

## Where to put new code

| You're adding... | Goes in |
|---|---|
| A new specialist agent | `backend/agents/<name>.py` + a prompt in `prompts/` (see EXTENDING.md → "Add a sub-agent") |
| A new tool | `backend/tools/<area>.py`, register in `tools/registry.py`, bind to an agent's `tool_names` |
| New prompt wording | the per-agent file in `backend/agents/prompts/` |
| Switching prompt versions | `backend/agents/prompts/active.toml` |
| Patient details (meds, contacts) | `backend/agents/prompts/_base.py` (once, everywhere) |
| A new event type | `backend/events/types.py` |
| A new DB table | `backend/db/models.py` |
| A new UI page | `frontend/src/app/<name>/page.tsx` |
| A new demo scenario | a `.txt` for `phase0.py`, a line in `try_live.py`, or `tests/scenarios/` |

## How it runs

**Today it's one process.** `guardian-backend` (FastAPI) hosts the router, the six
specialists, the tools, the event bus, and the DB; `phase0.py` can run the same
graph as a single CLI process for a fast sanity check. The `orchestrator/`,
`always_on/`, and `workers/` packages sketch a future three-process split (a
sensor tier and slow-time workers) but are **not wired** — don't let their
presence suggest the app needs them. It doesn't.
