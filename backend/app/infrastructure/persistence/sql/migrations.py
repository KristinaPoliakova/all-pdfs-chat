from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[4]
_ALEMBIC_INI = _BACKEND_ROOT / "alembic.ini"


class SchemaRevisionError(RuntimeError):
    """Raised when the database schema is not at the Alembic head revision."""


def to_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql+asyncpg://")
    return database_url


def alembic_config(database_url: str) -> Config:
    config = Config(str(_ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", to_sync_database_url(database_url))
    return config


def get_head_revision() -> str:
    script = ScriptDirectory.from_config(Config(str(_ALEMBIC_INI)))
    head = script.get_current_head()
    if head is None:
        msg = "No Alembic head revision found"
        raise RuntimeError(msg)
    return head


def get_current_revision(database_url: str) -> str | None:
    engine = create_engine(to_sync_database_url(database_url), poolclass=NullPool)
    try:
        with engine.connect() as connection:
            try:
                row = connection.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            except ProgrammingError:
                connection.rollback()
                return None
            return row[0] if row is not None else None
    finally:
        engine.dispose()


def upgrade_to_head(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")


def downgrade_to_base(database_url: str) -> None:
    command.downgrade(alembic_config(database_url), "base")


def stamp_to_head(database_url: str) -> None:
    command.stamp(alembic_config(database_url), "head")


def _legacy_schema_present(database_url: str) -> bool:
    engine = create_engine(to_sync_database_url(database_url), poolclass=NullPool)
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT 1 FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename = 'users' LIMIT 1"
                )
            ).fetchone()
            return row is not None
    finally:
        engine.dispose()


def ensure_migrated(database_url: str) -> None:
    """Apply pending migrations, or stamp legacy create_all databases at head."""
    head = get_head_revision()
    current = get_current_revision(database_url)
    if current == head:
        return
    if current is None and _legacy_schema_present(database_url):
        stamp_to_head(database_url)
        return
    upgrade_to_head(database_url)


def ensure_schema_current(*, database_url: str, strict: bool) -> None:
    head = get_head_revision()
    current = get_current_revision(database_url)
    if current == head:
        return

    message = (
        f"Database schema is not at Alembic head (current={current!r}, head={head!r}). "
        "Run: uv run alembic upgrade head"
    )
    if strict:
        raise SchemaRevisionError(message)
    logger.warning(message)
