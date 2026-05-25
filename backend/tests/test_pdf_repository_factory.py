from unittest.mock import patch

import pytest
from app.config.settings import _BACKEND_ROOT, Settings
from app.infrastructure.factories.pdf import create_pdf_repository, reset_pdf_repository_state
from app.infrastructure.persistence.sql.lifecycle import get_database
from app.infrastructure.persistence.sql.repositories.pdf import SqlPdfRepository
from app.infrastructure.persistence.sql.sqlite_paths import sqlite_file_path


@pytest.fixture(autouse=True)
async def _reset_factory() -> None:
    await reset_pdf_repository_state()
    yield
    await reset_pdf_repository_state()


@pytest.mark.asyncio
async def test_factory_uses_sqlite_url_for_dev() -> None:
    settings = Settings(
        app_env="dev",
        database_url="sqlite+aiosqlite:///./test-dev.db",
        _env_file=None,
    )

    store = create_pdf_repository(settings)

    assert isinstance(store, SqlPdfRepository)
    assert (
        sqlite_file_path(get_database(settings).database_url)
        == (_BACKEND_ROOT / "test-dev.db").resolve()
    )


@pytest.mark.asyncio
async def test_factory_uses_azure_sql_connectionstring_for_prod() -> None:
    settings = Settings(
        app_env="prod",
        azure_sql_connectionstring=(
            "Server=tcp:host,1433;Initial Catalog=db;User ID=u;Password=p;"
        ),
        azure_storage_connection_string="blob-conn",
        _env_file=None,
    )

    store = create_pdf_repository(settings)

    assert isinstance(store, SqlPdfRepository)
    assert get_database(settings).database_url.startswith("mssql+aioodbc:///?odbc_connect=")


def test_settings_rejects_prod_missing_azure_sql_url() -> None:
    with pytest.raises(ValueError, match="AZURE_SQL_CONNECTIONSTRING"):
        Settings(
            app_env="prod",
            azure_storage_connection_string="blob-conn",
            _env_file=None,
        )


@pytest.mark.asyncio
async def test_factory_returns_cached_singleton() -> None:
    with patch("app.infrastructure.persistence.sql.lifecycle.get_settings") as get_settings:
        get_settings.return_value = Settings(app_env="dev", _env_file=None)
        first = create_pdf_repository()
        second = create_pdf_repository()

    assert first is second
