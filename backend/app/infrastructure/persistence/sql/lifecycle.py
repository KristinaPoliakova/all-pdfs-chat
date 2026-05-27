from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.infrastructure.persistence.sql.azure_sql import resolve_prod_database_url
from app.infrastructure.persistence.sql.runtime import DatabaseRuntime
from app.infrastructure.persistence.sql.sqlite_paths import is_sqlite_database_url

_runtime: DatabaseRuntime | None = None


def _database_url_for(*, cfg: Settings) -> str:
    if cfg.is_prod:
        db_url = cfg.database_url.strip()
        if db_url and not is_sqlite_database_url(db_url):
            return cfg.database_url
        if cfg.azure_sql_connectionstring.strip():
            return resolve_prod_database_url(
                azure_sql_connectionstring=cfg.azure_sql_connectionstring,
            )
    return cfg.database_url


def get_database(settings: Settings | None = None) -> DatabaseRuntime:
    """Return the process database runtime.

    With explicit settings, returns a fresh runtime for tests/factory checks without
    replacing the process singleton.
    """
    if settings is not None:
        return DatabaseRuntime(_database_url_for(cfg=settings))

    global _runtime
    if _runtime is None:
        _runtime = DatabaseRuntime(_database_url_for(cfg=get_settings()))
    return _runtime


async def init_database(settings: Settings | None = None) -> None:
    await get_database(settings).init_schema()


async def close_database() -> None:
    global _runtime
    if _runtime is not None:
        await _runtime.close()
    _runtime = None


async def reset_database_state() -> None:
    await close_database()
