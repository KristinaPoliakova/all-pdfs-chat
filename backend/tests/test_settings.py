from pathlib import Path

import pytest
from app.config.settings import (
    DEFAULT_DEV_DATABASE_URL,
    DEFAULT_LOCAL_STORAGE_PATH,
    LOCAL_STORAGE_PATH,
    Settings,
    get_settings,
)

_POSTGRES_URL = "postgresql+asyncpg://app:secret@127.0.0.1:5432/all_pdfs_chat"


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
    monkeypatch.setenv("DATABASE_URL", _POSTGRES_URL)
    monkeypatch.setenv("STORAGE_BACKEND", "azure")
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "conn")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER_NAME", "uploads")

    settings = Settings(_env_file=None)

    assert settings.app_env == "prod"
    assert settings.database_url == _POSTGRES_URL
    assert settings.storage_backend == "azure"
    assert settings.azure_storage_connection_string == "conn"
    assert settings.azure_storage_container_name == "uploads"


def test_local_storage_path_is_default_under_backend_root() -> None:
    assert LOCAL_STORAGE_PATH == DEFAULT_LOCAL_STORAGE_PATH
    settings = Settings(app_env="dev", _env_file=None)
    assert settings.resolved_local_storage_path == DEFAULT_LOCAL_STORAGE_PATH


def test_resolved_local_storage_path_honors_override(tmp_path: Path) -> None:
    settings = Settings(
        app_env="prod",
        database_url=_POSTGRES_URL,
        local_storage_path=str(tmp_path / "uploads"),
        _env_file=None,
    )

    assert settings.resolved_local_storage_path == (tmp_path / "uploads").resolve()


def test_defaults_to_dev(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty_env = tmp_path / ".env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(_env_file=empty_env)

    assert settings.is_dev is True
    assert settings.is_prod is False
    assert settings.storage_backend == "local"
    assert settings.database_url == DEFAULT_DEV_DATABASE_URL
    assert settings.azure_storage_container_name == "pdfs"
    assert settings.classification_max_pages == 10


def test_loads_from_dotenv_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"APP_ENV=prod\nDATABASE_URL={_POSTGRES_URL}\nSTORAGE_BACKEND=local\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)

    settings = Settings(_env_file=env_file)

    assert settings.is_prod is True
    assert settings.database_url == _POSTGRES_URL
    assert settings.storage_backend == "local"


def test_normalizes_development_and_production_aliases() -> None:
    dev = Settings(app_env="development", _env_file=None)
    prod = Settings(
        app_env="production",
        database_url=_POSTGRES_URL,
        _env_file=None,
    )

    assert dev.is_dev is True
    assert prod.is_prod is True


def test_prod_accepts_local_storage_with_database_url() -> None:
    settings = Settings(
        app_env="prod",
        database_url=_POSTGRES_URL,
        storage_backend="local",
        _env_file=None,
    )

    assert settings.uses_local_storage is True
    assert settings.uses_azure_storage is False


def test_rejects_non_postgresql_database_url() -> None:
    with pytest.raises(ValueError, match="PostgreSQL async driver"):
        Settings(
            app_env="dev",
            database_url="sqlite+aiosqlite:///./data/app.db",
            _env_file=None,
        )


def test_prod_azure_storage_requires_connection_string() -> None:
    with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING"):
        Settings(
            app_env="prod",
            database_url=_POSTGRES_URL,
            storage_backend="azure",
            _env_file=None,
        )


def test_prod_parsing_enabled_requires_di_endpoint() -> None:
    with pytest.raises(ValueError, match="AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"):
        Settings(
            app_env="prod",
            database_url=_POSTGRES_URL,
            parsing_enabled=True,
            _env_file=None,
        )


def test_rejects_invalid_storage_backend() -> None:
    with pytest.raises(ValueError, match="STORAGE_BACKEND"):
        Settings(storage_backend="s3", _env_file=None)


def test_rejects_invalid_max_upload_size() -> None:
    with pytest.raises(ValueError, match="MAX_UPLOAD_SIZE_BYTES"):
        Settings(max_upload_size_bytes=0, _env_file=None)


def test_agent_settings_have_defaults() -> None:
    from tests.settings_helpers import make_test_settings

    settings = make_test_settings()

    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "llama3.1"
    assert settings.agent_search_top_k == 4
    assert settings.agent_max_tool_iterations == 5
    assert settings.agent_timeout_seconds == 60
    assert settings.agent_tool_char_limit == 6000


def test_tracing_settings_have_defaults() -> None:
    from tests.settings_helpers import make_test_settings

    settings = make_test_settings()

    assert settings.tracing_enabled is False
    assert settings.mlflow_tracking_uri == ""
    assert settings.mlflow_experiment == "all-pdfs-chat-agent"


def test_request_tracing_settings_have_defaults() -> None:
    from tests.settings_helpers import make_test_settings

    settings = make_test_settings()

    assert settings.request_tracing_enabled is False
    assert settings.request_trace_sample_ratio == 1.0
    assert settings.mlflow_http_experiment == "all-pdfs-chat-http"
