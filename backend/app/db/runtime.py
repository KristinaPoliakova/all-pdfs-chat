from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.sqlite_paths import ensure_sqlite_parent_dir

# Azure SQL cold start (auto-pause resume) and slow networks can exceed ODBC's ~15s default.
_AZURE_SQL_LOGIN_TIMEOUT_SECONDS = 60


def _create_app_async_engine(database_url: str) -> AsyncEngine:
    kwargs: dict[str, object] = {
        "echo": False,
        "pool_pre_ping": True,
    }
    if database_url.startswith("mssql+"):
        kwargs["connect_args"] = {"timeout": _AZURE_SQL_LOGIN_TIMEOUT_SECONDS}
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
            self._engine = _create_app_async_engine(self.database_url)
        return self._engine
