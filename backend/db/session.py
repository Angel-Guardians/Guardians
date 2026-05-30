"""SQLModel engine + session factory."""
from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from backend.config import settings

# SQLite by default (zero-setup local dev). Point DATABASE_URL at Postgres for the
# pgvector RAG upgrade (see docker-compose.yml). `pool_pre_ping` recycles stale
# connections that a container restart or idle timeout may have dropped.
_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=not _is_sqlite,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


def init_db() -> None:
    """Create tables. Use Alembic migrations in production."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with Session(engine) as session:
        yield session
