"""SQLModel engine + session factory."""
from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from backend.config import settings

# `check_same_thread=False` for SQLite is fine because we use sessions
# scoped per request. In production switch to SQLCipher (Phase 7).
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)


def init_db() -> None:
    """Create tables. Use Alembic migrations in production."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with Session(engine) as session:
        yield session
