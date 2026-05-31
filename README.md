# Guardian — Home Emergency AI Companion

> **New to the repo?** Read [`ONBOARDING.md`](ONBOARDING.md) for a guided reading
> path, and [`ARCHITECTURE.md`](ARCHITECTURE.md) / [`CODEBASE_MAP.md`](CODEBASE_MAP.md)
> for the design.

A multi-agent home-care companion. A hybrid router sends each message to one of
**six specialist agents** (safety, health, reminder, behavior, caregiver liaison,
companion); agents call tools (911 dispatch, caregiver SMS, schedule, vitals,
cool-space lookup, person-history recall) through a tool loop. Everything talks to
a **provider-neutral LLM seam**, so the same code runs on **OpenAI cloud today**
and a **local NVIDIA DGX Spark** later — only `.env` changes.

```
                 POST /turn (text)            GET /events/sse
 Watch ─vitals─▶  FastAPI  ─▶ GuardianAgent (LangGraph) ─▶ events ─▶ Web / Flutter UI
                    │            router ─▶ 6 specialists ─▶ tools
                    └─ SQLite/Postgres (profile, vitals, event log)
```

---

## Parts of the system

| Part | Path | Stack | Talks to |
|---|---|---|---|
| **Backend / API** | `backend/` | Python 3.11+, FastAPI, LangGraph, SQLModel | the LLM, the DB, every client |
| **Web dashboard** | `frontend/` | Next.js 16 + Tailwind + shadcn | backend HTTP + SSE |
| **Mobile/desktop app** | `flutter_frontend/` | Flutter (Dart) | backend HTTP |
| **Smartwatch** | `watch/` | Wear OS (Kotlin) | `POST /vitals/ingest` |
| **Scripts** | `scripts/` | Python | run the agent headless / seed / inject data |

The backend is the hub — **start it first**; every UI is optional and connects to
it over HTTP. The database (SQLite by default) auto-creates and seeds two demo
patients (**Eleanor** and **Sarah**) on first run.

---

## Prerequisites

- **Python 3.11+** (on this Windows host, use the `C:\Python313` interpreter — see
  [`CLAUDE.md`](CLAUDE.md)).
- **Node.js 20+** and npm (for the web frontend).
- An **OpenAI API key** (or a local DGX Spark endpoint — see below).
- Optional: **Docker** (only for the pgvector RAG upgrade), **Flutter SDK 3.3+**
  (mobile app), **Android Studio / JDK 21** (watch app).

---

## 1. Backend / API (start here)

```bash
cp .env.example .env          # then set LLM_API_KEY=sk-...   (LLM_MODEL=gpt-4o-mini)
pip install -e ".[dev]"       # installs the `guardian` package + dev tools
```

Run the API (FastAPI on **:8000**, SQLite auto-seeded):

```bash
guardian-backend                              # console script
# or, equivalently (use this on Windows if the script isn't on PATH):
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

> **Windows note:** the pip console scripts (`guardian-backend`, `guardian-seed`)
> are often off-PATH. Use the `python -m …` forms, and run from the **repo root** —
> the SQLite path `sqlite:///./guardian.db` is relative to your working directory.

Talk to Guardian over HTTP:

```bash
curl -s localhost:8000/turn/ -H 'content-type: application/json' \
  -d '{"text":"I fell and my chest feels tight", "patient_id":1}' | jq
# -> {"route":"safety","reply":"...","tool_calls":[{"tool":"call_911",...}]}
```

The routing decision, every tool call, and the spoken reply also stream onto
`GET /events/sse`, so the **Live** page updates in real time.
Interactive API docs: <http://localhost:8000/docs>.

### Headless (no UI)

```bash
python scripts/phase0.py                 # type a message (text-in / text-out)
python scripts/phase0.py --patient Sarah # run as a specific seeded patient
python scripts/try_live.py               # 5 scripted inputs through the real model
```

---

## 2. Web dashboard (`frontend/`)

```bash
cd frontend
npm install
npm run dev          # Next.js on http://localhost:3000
```

Point at a non-default backend with `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

**On first load you pick a profile** ("Who's using Guardian?"). From the avatar
menu in the header you can switch profiles, create a new one, or log out. The
chosen profile drives every page *and* the agent's context, so the backend must be
running for the picker to list patients.

> Next.js 16 allows only **one `next dev` per project** — if `:3000` is taken, stop
> the existing server first. See [`frontend/CLAUDE.md`](frontend/CLAUDE.md).

Build / lint: `npm run build`, `npm run lint`.

---

## 3. Mobile / desktop app (`flutter_frontend/`)

A mobile-first Flutter client mirroring the web UI (Home, Vitals, Talk, Care,
Profile, Location, Medical history). Details in
[`flutter_frontend/README.md`](flutter_frontend/README.md).

```bash
cd flutter_frontend
flutter pub get
flutter run            # pick a connected device / emulator
```

The default backend URL is `http://10.0.2.2:8000` (the host machine as seen from an
Android emulator). Change it at runtime from the in-app **Settings** dialog (it's
persisted) — for a physical device use your machine's LAN IP, e.g.
`http://192.168.1.50:8000`.

---

## 4. Smartwatch (`watch/`)

A standalone **Wear OS** app that records heart rate / steps / calories offline and
POSTs unsent readings to the backend every ~60s. Full instructions in
[`watch/README.md`](watch/README.md).

1. Open the **`watch/`** folder in Android Studio as its own project; let it sync.
2. Pick a watch device/emulator and **Run** the `app` configuration; grant the
   sensor/activity/notification permissions on first launch.
3. On the watch, open **Settings** → set **Backend URL** to your dev machine's LAN
   IP (e.g. `http://192.168.1.50:8000`) and **Patient ID** (default `1`), then
   toggle **Monitoring** on. Vitals show up on the web/Flutter **Vitals** page.

Optional: bake in a default URL via `guardian.baseUrl=http://192.168.1.50:8000` in
`watch/gradle.properties`. Toolchain: JDK 21, Android SDK, AGP 8.9.1 /
Gradle 8.11.1, compileSdk 36. The watch and backend host must be on the same LAN.

---

## Configuration (`.env`)

Copy `.env.example` → `.env`. The important knobs:

| Variable | Purpose |
|---|---|
| `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | the LLM backend (cloud or local). |
| `DATABASE_URL` | `sqlite:///./guardian.db` (default) or a Postgres URL. |
| `TWILIO_*` | real SMS/calls for the safety/caregiver tools (optional in dev). |
| `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` | optional tracing (no-op if unset). |
| `MEMORY_BACKEND` | `keyword` (default) or `pgvector` for RAG recall. |
| `LAB_DOCUMENTS_DIR` | where uploaded lab-result PDFs are stored. |

Switching cloud ↔ local DGX Spark is a change to the `LLM_*` block **only** — no
code changes. See [`SETUP_DGX_SPARK.md`](SETUP_DGX_SPARK.md) and [`MODELS.md`](MODELS.md).
Short version: SSH-tunnel Ollama from the Spark, then set
`LLM_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=nemotron-3-nano:4b`,
`LLM_API_KEY=not-needed`.

---

## Database

- **SQLite by default** — zero setup. Tables are created and the schema is
  auto-migrated (missing columns added) on backend startup; demo patients Eleanor
  and Sarah are seeded if the DB is empty.
- Re-seed manually: `python -c "from backend.db.seed import seed_all; seed_all()"`.
- **Postgres / pgvector (optional, for RAG):**
  ```bash
  docker compose up -d postgres
  # in .env: DATABASE_URL=postgresql+psycopg://guardian:guardian@localhost:5432/guardian
  pip install -e ".[rag]"
  ```

---

## Testing & quality

```bash
python -m pytest               # run the suite (from the repo root)
ruff check backend tests scripts
ruff format backend tests scripts
```

Notes: the testcontainers-**Postgres** tests need Docker and error out without it;
the **smoke** test places a real Twilio call and fails with HTTP 401 unless valid
`TWILIO_*` creds are set. Both are environmental, not code failures.

---

## Observability

Set `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY=...`. You get one span per graph
node (which specialist ran) with model and tool calls nested beneath — "which
agents called which tools", end to end. No code change; no-op when unset.

---

## Repo layout

```
backend/
  llm/          provider-neutral LLM seam (the ONLY place that imports `openai`)
  agents/       guardian.py (router) + graph.py (LangGraph) + 6 specialists + base
  tools/        registry + stubs: emergency, health, reminder, civic, memory
  api/          turn.py (POST /turn), vitals.py (watch), events_sse.py, patient.py, lab_records.py
  events/       bus.py (in-proc pub/sub) + types.py (event models)
  services/     patient_profile, lab_records, … (business logic)
  db/           SQLModel models, session (engine + auto-migrate), seed
  voice/, always_on/, workers/   ── audio / sensor-event tier (partly stubbed)
frontend/          Next.js 16 + Tailwind + shadcn (Live / Vitals / Reminders / Profile)
flutter_frontend/  Flutter mobile/desktop client
watch/             Wear OS app — real vitals -> POST /vitals/ingest every 60s
data/personas/     markdown life-history notes (RAG source)
scripts/           phase0.py, try_live.py, seed_patient.py, inject_vital.py, demo_reset.py
```

See [`EXTENDING.md`](EXTENDING.md) to add a scenario, tool, agent, or persona, and
[`MERGE_NOTES.md`](MERGE_NOTES.md) for what came from which original branch.
