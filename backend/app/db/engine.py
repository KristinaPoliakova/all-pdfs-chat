from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Azure SQL cold start (auto-pause resume) and slow networks can exceed ODBC's ~15s default.
_AZURE_SQL_LOGIN_TIMEOUT_SECONDS = 60


def create_app_async_engine(database_url: str) -> AsyncEngine:
    kwargs: dict[str, object] = {
        "echo": False,
        "pool_pre_ping": True,
    }
    if database_url.startswith("mssql+"):
        kwargs["connect_args"] = {"timeout": _AZURE_SQL_LOGIN_TIMEOUT_SECONDS}
    return create_async_engine(database_url, **kwargs)
