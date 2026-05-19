from pathlib import Path

import pytest
from app.config.settings import LOCAL_STORAGE_PATH, Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_get_settings_returns_cached_singleton() -> None:
    first = get_settings()
    second = get_settings()

    assert first is second


def test_reads_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "conn")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER_NAME", "uploads")
    monkeypatch.setenv("AZURE_SQL_DATABASE_URL", "mssql+aioodbc://user:pass@host/db")

    settings = Settings()

    assert settings.app_env == "prod"
    assert settings.azure_storage_connection_string == "conn"
    assert settings.azure_storage_container_name == "uploads"


def test_local_storage_path_is_fixed() -> None:
    assert LOCAL_STORAGE_PATH == Path("data/uploads")


def test_defaults_to_dev(tmp_path: Path) -> None:
    empty_env = tmp_path / ".env"
    empty_env.write_text("", encoding="utf-8")
    settings = Settings(_env_file=empty_env)

    assert settings.is_dev is True
    assert settings.is_prod is False
    assert settings.azure_storage_container_name == "pdfs"


def test_loads_from_dotenv_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=prod\n"
        "AZURE_STORAGE_CONNECTION_STRING=from-dotenv\n"
        "AZURE_STORAGE_CONTAINER_NAME=pdfs-prod\n"
        "AZURE_SQL_DATABASE_URL=mssql+aioodbc://user:pass@host/db\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("AZURE_STORAGE_CONTAINER_NAME", raising=False)

    settings = Settings(_env_file=env_file)

    assert settings.is_prod is True
    assert settings.azure_storage_connection_string == "from-dotenv"
    assert settings.azure_storage_container_name == "pdfs-prod"


def test_normalizes_development_and_production_aliases() -> None:
    dev = Settings(app_env="development")
    prod = Settings(
        app_env="production",
        azure_storage_connection_string="conn",
        azure_sql_database_url="mssql+aioodbc://user:pass@host/db",
    )

    assert dev.is_dev is True
    assert prod.is_prod is True


def test_prod_requires_azure_configuration() -> None:
    with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING"):
        Settings(app_env="prod", azure_sql_database_url="mssql+aioodbc://x")


def test_rejects_invalid_max_upload_size() -> None:
    with pytest.raises(ValueError, match="MAX_UPLOAD_SIZE_BYTES"):
        Settings(max_upload_size_bytes=0)
