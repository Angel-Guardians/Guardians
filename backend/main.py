"""FastAPI entrypoint.

Hosts the on-demand tier: the LangGraph GuardianAgent (six specialists behind a
hybrid router), the Tool Bus, the Event Bus, and the HTTP/SSE API. The agent is
provider-neutral — it talks only to backend.llm, so the exact same process runs
against OpenAI cloud today and a local DGX Spark endpoint later by changing .env.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.api import events_sse, patient, turn, vitals
from backend.config import settings
from backend.events.bus import EventBus
from backend.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()

    from backend.db.session import init_db

    init_db()
    from backend.db.seed import seed_if_empty

    seed_if_empty()

    # Event bus: in-process pub/sub. SSE clients subscribe; /turn publishes.
    app.state.event_bus = EventBus()
    await app.state.event_bus.start()

    # Build the orchestrator once. If the LLM isn't configured yet (no key), don't
    # crash the whole API — log it; /turn will surface the error on first use.
    try:
        from backend.agents.guardian import GuardianAgent

        app.state.guardian = GuardianAgent()
        logger.info("GuardianAgent ready (LLM via backend.llm).")
    except Exception as exc:  # noqa: BLE001
        app.state.guardian = None
        logger.warning(f"GuardianAgent not initialised: {exc}")

    yield

    await app.state.event_bus.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Guardian",
        version="0.2.0",
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

    app.include_router(patient.router, prefix="/patient", tags=["patient"])
    app.include_router(events_sse.router, prefix="/events", tags=["events"])
    app.include_router(turn.router, prefix="/turn", tags=["turn"])
    app.include_router(vitals.router, prefix="/vitals", tags=["vitals"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        ready = getattr(app.state, "guardian", None) is not None
        return {"status": "ok", "guardian": "ready" if ready else "unconfigured"}

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"message": "pong"}

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
