"""FastAPI entrypoint.

Hosts the on-demand tier: Orchestrator + Sub-Agents + Tool Bus + API.
Always-on services run in a separate process (`guardian-always-on`).
Slow-time workers run in a third process (`guardian-workers`).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import events_sse, patient
from backend.config import settings
from backend.events.bus import EventBus
from backend.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown hooks.

    Wire here:
      - Event bus (NATS or asyncio.Queue)
      - Orchestrator + Sub-Agents
      - APScheduler for reminders
      - DB engine
      - LLM client (Ollama)
    """
    configure_logging()
    from backend.db.session import init_db

    init_db()
    from backend.db.seed import seed_if_empty

    seed_if_empty()
    app.state.event_bus = EventBus()
    # TODO: start orchestrator, scheduler, subscribe sub-agents to bus
    yield
    # TODO: graceful shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title="Guardian",
        version="0.1.0",
        description="Home Emergency AI Companion",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(patient.router, prefix="/patient", tags=["patient"])
    app.include_router(events_sse.router, prefix="/events", tags=["events"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"message": "pong"}

    return app


app = create_app()


def run() -> None:
    """Entrypoint for `guardian-backend` script."""
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
