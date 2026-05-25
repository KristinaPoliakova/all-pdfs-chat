from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from app.db.base import Base
from app.db.engine import create_app_async_engine
from app.db.sqlite_paths import ensure_sqlite_parent_dir


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

    async def init_schema(self) -> None:
        ensure_sqlite_parent_dir(self.database_url)
        engine = self._get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._session_factory = None

    def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_app_async_engine(self.database_url)
        return self._engine
