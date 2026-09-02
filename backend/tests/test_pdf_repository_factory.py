from unittest.mock import patch

import pytest
from app.config.settings import DEFAULT_DEV_DATABASE_URL, Settings
from app.infrastructure.factories.pdf import create_pdf_repository
from app.infrastructure.persistence.sql.lifecycle import get_database
from app.infrastructure.persistence.sql.repositories.pdf import SqlPdfRepository

_POSTGRES_URL = "postgresql+asyncpg://app:secret@127.0.0.1:5432/all_pdfs_chat"


@pytest.mark.asyncio
async def test_factory_uses_postgres_url_for_dev() -> None:
    settings = Settings(
        app_env="dev",
        database_url=_POSTGRES_URL,
        _env_file=None,
    )

    store = create_pdf_repository(settings)

    assert isinstance(store, SqlPdfRepository)
    assert get_database(settings).database_url == _POSTGRES_URL


@pytest.mark.asyncio
async def test_factory_uses_postgres_url_for_prod() -> None:
    settings = Settings(
        app_env="prod",
        database_url=_POSTGRES_URL,
        _env_file=None,
    )

    store = create_pdf_repository(settings)

    assert isinstance(store, SqlPdfRepository)
    assert get_database(settings).database_url == _POSTGRES_URL


def test_settings_rejects_non_postgresql_database_url() -> None:
    with pytest.raises(ValueError, match="PostgreSQL async driver"):
        Settings(
            app_env="dev",
            database_url="sqlite+aiosqlite:///./data/app.db",
            _env_file=None,
        )


def test_settings_default_dev_database_url_is_postgresql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(app_env="dev", _env_file=None)

    assert settings.database_url == DEFAULT_DEV_DATABASE_URL


@pytest.mark.asyncio
async def test_factory_builds_sql_pdf_repository() -> None:
    with patch("app.infrastructure.persistence.sql.lifecycle.get_settings") as get_settings:
        get_settings.return_value = Settings(app_env="dev", _env_file=None)
        store = create_pdf_repository()

    assert isinstance(store, SqlPdfRepository)
