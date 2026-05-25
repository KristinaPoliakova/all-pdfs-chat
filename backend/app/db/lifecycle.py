from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.db.database_url import database_url_for
from app.db.runtime import DatabaseRuntime

_runtime: DatabaseRuntime | None = None


def get_database(settings: Settings | None = None) -> DatabaseRuntime:
    """Return the process database runtime.

    With explicit settings, returns a fresh runtime for tests/factory checks without
    replacing the process singleton.
    """
    if settings is not None:
        return DatabaseRuntime(database_url_for(cfg=settings))

    global _runtime
    if _runtime is None:
        _runtime = DatabaseRuntime(database_url_for(cfg=get_settings()))
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
