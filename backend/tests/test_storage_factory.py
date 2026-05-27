from unittest.mock import patch

import pytest
from app.config.settings import DEFAULT_LOCAL_STORAGE_PATH, Settings
from app.infrastructure.factories.storage import create_file_storage
from app.infrastructure.storage.local import LocalFileStorage

_POSTGRES_URL = "postgresql+asyncpg://app:secret@127.0.0.1:5432/all_pdfs_chat"


def test_factory_uses_local_for_dev_settings() -> None:
    settings = Settings(app_env="dev", _env_file=None)

    storage = create_file_storage(settings)

    assert isinstance(storage, LocalFileStorage)
    assert storage._base_dir == DEFAULT_LOCAL_STORAGE_PATH


def test_factory_uses_local_for_prod_when_storage_backend_local() -> None:
    settings = Settings(
        app_env="prod",
        database_url=_POSTGRES_URL,
        storage_backend="local",
        _env_file=None,
    )

    storage = create_file_storage(settings)

    assert isinstance(storage, LocalFileStorage)
    assert storage._base_dir == DEFAULT_LOCAL_STORAGE_PATH


def test_factory_uses_custom_local_path_for_prod() -> None:
    settings = Settings(
        app_env="prod",
        database_url=_POSTGRES_URL,
        storage_backend="local",
        local_storage_path="/var/lib/all-pdfs-chat/uploads",
        _env_file=None,
    )

    storage = create_file_storage(settings)

    assert isinstance(storage, LocalFileStorage)
    assert storage._base_dir == settings.resolved_local_storage_path


def test_factory_uses_azure_for_prod_when_storage_backend_azure() -> None:
    settings = Settings(
        app_env="prod",
        database_url=_POSTGRES_URL,
        storage_backend="azure",
        azure_storage_connection_string="UseDevelopmentStorage=true",
        azure_storage_container_name="pdfs",
        _env_file=None,
    )

    with patch("app.infrastructure.storage.azure.BlobServiceClient"):
        storage = create_file_storage(settings)

    assert storage.__class__.__name__ == "AzureBlobStorage"


def test_factory_uses_get_settings_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")

    storage = create_file_storage()

    assert isinstance(storage, LocalFileStorage)


def test_settings_rejects_unknown_app_env() -> None:
    with pytest.raises(ValueError, match="Unknown APP_ENV"):
        Settings(app_env="staging", _env_file=None)
