"""SQLModel engine + session factory."""
from __future__ import annotations

from collections.abc import Iterator

from loguru import logger
from sqlalchemy import inspect, text
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
    """Create tables, then add any newly-declared columns. Use Alembic in production."""
    SQLModel.metadata.create_all(engine)
    _lightweight_migrate()


def _lightweight_migrate() -> None:
    """Add model columns that are missing from already-existing tables.

    `create_all()` only creates missing *tables* — it never alters an existing
    one. So when a model gains a column (e.g. ``patient.location`` / ``bio``), a
    pre-existing ``guardian.db`` would keep the old schema and every query that
    selects the new column would fail with ``no such column``. This walks the
    SQLModel metadata and issues ``ALTER TABLE ... ADD COLUMN`` for each missing
    column. SQLite-only by design; production runs on Postgres + Alembic, where
    this is a no-op.
    """
    if not _is_sqlite:
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # create_all() already made it with the full schema
            present = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                if not column.nullable and column.default is None and column.server_default is None:
                    # Can't back-fill a NOT NULL column without a default on an
                    # existing table; needs a real migration. Skip and warn.
                    logger.warning(
                        f"Skipping migration of NOT NULL column {table.name}.{column.name} "
                        "(no default); add it via a real migration."
                    )
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}')
                )
                logger.info(f"Migrated schema: added column {table.name}.{column.name} ({col_type})")


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with Session(engine) as session:
        yield session
