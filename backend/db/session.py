"""SQLModel engine + session factory."""
from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from backend.config import settings

# Postgres (psycopg 3) engine. `pool_pre_ping` recycles stale connections that
# a container restart or idle timeout may have dropped.
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)


def init_db() -> None:
    """Create tables. Use Alembic migrations in production."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with Session(engine) as session:
        yield session
