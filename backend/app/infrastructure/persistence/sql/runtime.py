from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_POSTGRES_POOL_SIZE = 5
_POSTGRES_MAX_OVERFLOW = 10
_POSTGRES_POOL_RECYCLE_SECONDS = 1800


def _create_app_async_engine(database_url: str) -> AsyncEngine:
    kwargs: dict[str, object] = {
        "echo": False,
        "pool_pre_ping": True,
    }
    if database_url.startswith("postgresql+"):
        kwargs["pool_size"] = _POSTGRES_POOL_SIZE
        kwargs["max_overflow"] = _POSTGRES_MAX_OVERFLOW
        kwargs["pool_recycle"] = _POSTGRES_POOL_RECYCLE_SECONDS
    return create_async_engine(database_url, **kwargs)


@dataclass
class DatabaseRuntime:
    database_url: str
    _engine: AsyncEngine | None = field(default=None, repr=False)
    _session_factory: async_sessionmaker[AsyncSession] | None = field(default=None, repr=False)

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            engine = self._get_engine()
            self._session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory

    async def verify_connection(self) -> None:
        async with self.session_factory() as session:
            await session.execute(text("SELECT 1"))

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._session_factory = None

    def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = _create_app_async_engine(self.database_url)
        return self._engine
