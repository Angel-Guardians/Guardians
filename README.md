# Guardian — Home Emergency AI Companion (merged main)

> **New to the repo? Read [`ONBOARDING.md`](ONBOARDING.md) first** — a 30-min shared
> reading path plus a per-person guide to the files that matter for your track.

A multi-agent home-care companion. A hybrid router sends each message to one of
**six specialist agents** (safety, health, reminder, behavior, caregiver liaison,
companion); agents call tools (911 dispatch, caregiver SMS, schedule, vitals,
cool-space lookup, person-history recall) through a tool loop. Everything talks to
a **provider-neutral LLM seam**, so the same code runs on **OpenAI cloud today**
and a **local NVIDIA DGX Spark** later — only `.env` changes.

```
                 POST /turn (text)            GET /events/sse
 Watch ─vitals─▶  FastAPI  ─▶ GuardianAgent (LangGraph) ─▶ events ─▶ Next.js UI
                    │            router ─▶ 6 specialists ─▶ tools
                    └─ SQLite/Postgres (profile, vitals, event log)
```

## Run it now (OpenAI, zero infra)

```bash
cp .env.example .env          # set LLM_API_KEY=sk-...   (LLM_MODEL=gpt-4o-mini)
pip install -e ".[dev]"

# A) text-in / text-out, single process (fastest sanity check)
python scripts/phase0.py            # type a message, or pass a .txt file path
python scripts/try_live.py          # 5 scripted inputs through the real model

# B) full API + UI
guardian-backend                    # FastAPI on :8000  (SQLite, auto-seeded Eleanor)
cd frontend && npm install && npm run dev   # Next.js on :3000
```

Talk to Guardian over HTTP:

```bash
curl -s localhost:8000/turn/ -H 'content-type: application/json' \
  -d '{"text":"I fell and my chest feels tight"}' | jq
# -> {"route":"safety","reply":"...","tool_calls":[{"tool":"call_911",...}]}
```

The routing decision, every tool call, and the spoken reply also stream onto
`GET /events/sse`, so the **Live** page lights up in real time.

## Switch to the DGX Spark

See **SETUP_DGX_SPARK.md** for the tunnel, and **MODELS.md** for which Nemotron
model to pick and the effort involved. Short version: SSH-tunnel Ollama from the
Spark, then in `.env` set `LLM_BASE_URL=http://localhost:11434/v1`,
`LLM_MODEL=nemotron-3-nano:4b`, `LLM_API_KEY=not-needed`. No code change.

## Observability

Set `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY=...`. You get one span per graph
node (which specialist ran) with the model calls and tool calls nested beneath —
"which agents called which tools", end to end. No code change; no-op when unset.

## Layout

```
backend/
  llm/          provider-neutral LLM seam (the ONLY place that imports `openai`)
  agents/       guardian.py (router) + graph.py (LangGraph) + 6 specialists + base
  tools/        registry + stubs: emergency, health, reminder, civic, memory
  api/          turn.py (POST /turn), vitals.py (watch), events_sse.py, patient.py
  events/       bus.py (in-proc pub/sub) + types.py (event models)
  db/           SQLModel models, session, seed
  orchestrator/, always_on/, workers/   ── NOT wired yet (sensor-event tier; stubs)
frontend/       Next.js 16 + Tailwind + shadcn (Live / Vitals / Reminders / Profile)
watch/          Wear OS app — real vitals -> POST /vitals/ingest every 60s
data/personas/  markdown life-history notes (RAG source)
scripts/        phase0.py, try_live.py, seed_patient.py, ...
```

See **EXTENDING.md** to add a scenario, tool, agent, or persona.
See **MERGE_NOTES.md** for what came from which original branch.
