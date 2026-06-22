from __future__ import annotations

from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.config.settings import Settings, get_settings

_pool: AsyncConnectionPool[Any] | None = None
_checkpointer: AsyncPostgresSaver | None = None

_CONNECTION_KWARGS = {"autocommit": True, "prepare_threshold": 0}


def _to_psycopg_conninfo(database_url: str) -> str:
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
        if database_url.startswith(prefix):
            return "postgresql://" + database_url.removeprefix(prefix)
    return database_url


async def init_chat_checkpointer(settings: Settings | None = None) -> None:
    global _pool, _checkpointer
    if _checkpointer is not None:
        return
    resolved = settings or get_settings()
    pool: AsyncConnectionPool[Any] = AsyncConnectionPool(
        conninfo=_to_psycopg_conninfo(resolved.database_url),
        max_size=10,
        kwargs=_CONNECTION_KWARGS,
        open=False,
    )
    await pool.open()
    try:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
    except BaseException:
        await pool.close()
        raise
    _pool = pool
    _checkpointer = checkpointer


def get_chat_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("chat checkpointer not initialized; call init_chat_checkpointer first")
    return _checkpointer


async def close_chat_checkpointer() -> None:
    global _pool, _checkpointer
    if _pool is not None:
        await _pool.close()
    _pool = None
    _checkpointer = None
