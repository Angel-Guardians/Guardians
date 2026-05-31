# Guardian — project guide for Claude

Home-emergency AI companion. A hybrid router sends each message to one of six
specialist agents (safety, health, reminder, behavior, caregiver, companion);
agents call tools through a tool loop. The LLM is reached only through a
**provider-neutral seam**, so the same code runs on OpenAI cloud or a local
NVIDIA DGX Spark by changing `.env` alone.

See [README.md](README.md) for full install/run instructions and
[ARCHITECTURE.md](ARCHITECTURE.md) / [CODEBASE_MAP.md](CODEBASE_MAP.md) for design.

## Parts of the system

- `backend/` — FastAPI + LangGraph agent + SQLModel DB + SSE event bus (Python).
- `frontend/` — Next.js 16 web dashboard (has its own [CLAUDE.md](frontend/CLAUDE.md)).
- `flutter_frontend/` — Flutter mobile/desktop client (mirrors the web UI).
- `watch/` — Wear OS app that streams real vitals to `POST /vitals/ingest`.
- `scripts/` — `phase0.py` (text in/out), `try_live.py`, `seed_patient.py`, etc.

## Environment & commands (Windows host)

- **Use the `C:\Python313` interpreter** for all backend work
  (`C:/Python313/python.exe`). The other Python installs / `.venv` do **not**
  have the deps; conda `base` is on PATH but is the wrong one.
- **pip console scripts (`guardian-backend`, `guardian-seed`) are off-PATH here.**
  Prefer module form: `python -m uvicorn backend.main:app` and
  `python -c "from backend.db.seed import seed_all; seed_all()"`. Makefile targets
  that call bare scripts will fail.
- **Run all backend/DB commands from the repo root.** `DATABASE_URL` is
  `sqlite:///./guardian.db` — **relative to the process cwd**. The PowerShell tool
  runs at the repo root; the Bash tool's cwd has been observed to be `frontend/`,
  which silently creates/migrates a stray `frontend/guardian.db` instead of the
  real one. Verify `os.getcwd()` before any DB write. See memory
  `guardians-dev-servers-and-cwd`.
- **DB schema auto-migrates on startup** (`init_db()` → `_lightweight_migrate()`
  adds missing columns for SQLite). There is no Alembic setup despite Makefile
  mentioning it. Seeds patients **Eleanor (#1)** and **Sarah (#2)** if empty.

## Frontend notes

- Next.js **16** + Turbopack: read `frontend/CLAUDE.md` — APIs differ from training
  data; consult `node_modules/next/dist/docs/` before writing Next code.
- **Only one `next dev` per project.** The user usually runs it on **:3000**, which
  blocks a second instance and the Claude Preview MCP — you cannot browser-drive
  the web UI here; verify with `tsc --noEmit`, `eslint`, and the dev log at
  `frontend/.next/dev/logs/next-development.log`.
- The active patient profile is a lightweight **session** stored in localStorage
  (`profile-storage.ts`): `getActivePatientId()` is `null` when logged out;
  `SessionGate` shows a profile picker until one is chosen.

## Testing

- `python -m pytest` from the repo root.
- **Docker is broken here**, so the testcontainers-Postgres tests (`db_session`
  fixture) error out — expected; use SQLite-backed paths for Docker-free checks.
- The smoke test places a real Twilio call and fails with **HTTP 401** unless valid
  `TWILIO_*` creds are set — environmental, not a code regression.

## Invariants to respect

- **`openai` is imported only in `backend/llm/`** (the provider seam). Never import
  a vendor SDK elsewhere; talk to the LLM through `backend.llm`.
- Tools are registered in `backend/tools/` and invoked via the registry/tool loop.
- Code style: `ruff` (line-length 100, py311). Run `ruff check`/`ruff format` on
  `backend tests scripts`.
- Don't commit secrets; `.env` is git-ignored (`.env.example` is the template).
