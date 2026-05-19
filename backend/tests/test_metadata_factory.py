from unittest.mock import patch

import pytest
from app.config.settings import Settings
from app.metadata.factory import create_pdf_metadata_store, reset_metadata_store_state
from app.metadata.sql import SqlPdfMetadataStore


@pytest.fixture(autouse=True)
async def _reset_factory() -> None:
    await reset_metadata_store_state()
    yield
    await reset_metadata_store_state()


@pytest.mark.asyncio
async def test_factory_uses_sqlite_url_for_dev() -> None:
    settings = Settings(
        app_env="dev",
        database_url="sqlite+aiosqlite:///./test-dev.db",
        _env_file=None,
    )

    store = create_pdf_metadata_store(settings)

    assert isinstance(store, SqlPdfMetadataStore)
    assert store._database_url == "sqlite+aiosqlite:///./test-dev.db"


@pytest.mark.asyncio
async def test_factory_uses_azure_sql_url_for_prod() -> None:
    settings = Settings(
        app_env="prod",
        azure_sql_database_url="mssql+aioodbc://user:pass@host/db",
        azure_storage_connection_string="blob-conn",
        _env_file=None,
    )

    store = create_pdf_metadata_store(settings)

    assert isinstance(store, SqlPdfMetadataStore)
    assert store._database_url == "mssql+aioodbc://user:pass@host/db"


def test_settings_rejects_prod_missing_azure_sql_url() -> None:
    with pytest.raises(ValueError, match="AZURE_SQL_DATABASE_URL"):
        Settings(
            app_env="prod",
            azure_storage_connection_string="blob-conn",
            _env_file=None,
        )


@pytest.mark.asyncio
async def test_factory_returns_cached_singleton() -> None:
    with patch("app.metadata.factory.get_settings") as get_settings:
        get_settings.return_value = Settings(app_env="dev", _env_file=None)
        first = create_pdf_metadata_store()
        second = create_pdf_metadata_store()

    assert first is second
