# Running Guardian with Docker

Guardian ships as two containers orchestrated by `docker-compose.yml`:

| Service    | Image source         | Port  | What it is                                            |
|------------|----------------------|-------|-------------------------------------------------------|
| `backend`  | `backend/Dockerfile` | 8000  | FastAPI + LangGraph API. Bundles `backend/`, `scripts/`, `scenarios/`, and `tests/`. |
| `frontend` | `frontend/Dockerfile`| 3000  | Next.js 16 UI.                                        |
| `postgres` | `pgvector/pgvector`  | 5432  | Optional pgvector store for the RAG upgrade (opt-in). |

> The `watch/` directory is an Android / Wear OS wearable client, not a server,
> so it is intentionally **not** part of the Docker stack.

## Prerequisites

- Docker Engine 24+ and the Docker Compose plugin (`docker compose version`).
- A `.env` file in the repo root. The backend reads it via `env_file: .env`.

```bash
cp .env.example .env
# then edit .env and set at least LLM_API_KEY (and LLM_* if not using OpenAI)
```

`.env` is git-ignored — every machine creates its own. Without a valid
`LLM_API_KEY` the API still starts, but `/health` reports
`"guardian": "unconfigured"` and `/turn` errors on first use.

## Quick start

Build and run the full stack (backend + frontend):

```bash
docker compose up --build
```

Then open:

- Frontend UI  → http://localhost:3000
- Backend API  → http://localhost:8000
- Health check → http://localhost:8000/health  → `{"status":"ok","guardian":"ready"}`
- API docs     → http://localhost:8000/docs

Run detached and view logs:

```bash
docker compose up -d --build
docker compose logs -f backend
```

Stop everything:

```bash
docker compose down          # keep volumes (SQLite DB persists)
docker compose down -v       # also delete the guardian-data / pgdata volumes
```

## Configuration notes

### Frontend → backend URL
`NEXT_PUBLIC_API_BASE_URL` is **baked into the client bundle at build time**
(Next.js inlines `NEXT_PUBLIC_*`). The browser — not the container — makes these
calls, so it defaults to `http://localhost:8000`. To point the UI at a different
host, set it before building:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.example.com docker compose build frontend
```

### Persistence
The `guardian-data` volume holds the SQLite DB (`/app/data`) so patient data and
seeds survive `docker compose down`. Use `down -v` to wipe it.

## Running scripts, tests, and scenarios

The backend image bundles `scripts/`, `scenarios/`, and `tests/`, so you can run
the dev surface inside the same container without a local Python setup.

```bash
# Test suite
docker compose run --rm backend pytest -q

# A specific test
docker compose run --rm backend pytest tests/unit/test_router.py

# Lint
docker compose run --rm backend ruff check backend tests scripts

# Utility scripts (entrypoints defined in pyproject)
docker compose run --rm backend python scripts/seed_patient.py
docker compose run --rm backend python scripts/demo_reset.py

# Scenario JSON lives at /app/scenarios inside the container
docker compose run --rm backend ls scenarios
```

## Optional: Postgres / pgvector (RAG)

Postgres is behind a Compose `profile`, so it does **not** start by default.
Bring it up only for the pgvector RAG upgrade:

```bash
docker compose --profile rag up -d postgres
```

Then point the backend at it in `.env` and restart `backend`:

```env
DATABASE_URL=postgresql+psycopg://guardian:guardian@postgres:5432/guardian
MEMORY_BACKEND=pgvector
```

> Use host `postgres` (the service name) from inside the Compose network, or
> `localhost` when connecting from your host machine.

## Building images individually

```bash
# Backend build context MUST be the repo root (it bundles sibling dirs):
docker build -f backend/Dockerfile -t guardian-backend .

# Frontend build context is the frontend dir:
docker build -f frontend/Dockerfile -t guardian-frontend ./frontend
```

## Troubleshooting

- **`permission denied ... /var/run/docker.sock`** — your user isn't in the
  `docker` group. Either add it (`sudo usermod -aG docker $USER`, then re-login)
  or prefix commands with `sudo`.
- **`/health` shows `"unconfigured"`** — `LLM_API_KEY` is missing/invalid in
  `.env`. Fix it and `docker compose restart backend`.
- **Frontend calls fail in the browser** — it was built with the wrong
  `NEXT_PUBLIC_API_BASE_URL`. Rebuild the frontend with the correct value.
