from unittest.mock import patch

import pytest
from app.config.settings import LOCAL_STORAGE_PATH, Settings
from app.storage.factory import create_file_storage
from app.storage.local import LocalFileStorage


def test_factory_uses_local_for_dev_settings() -> None:
    settings = Settings(app_env="dev", _env_file=None)

    storage = create_file_storage(settings)

    assert isinstance(storage, LocalFileStorage)
    assert storage._base_dir == LOCAL_STORAGE_PATH


def test_factory_uses_azure_for_prod_settings() -> None:
    settings = Settings(
        app_env="prod",
        azure_storage_connection_string="UseDevelopmentStorage=true",
        azure_storage_container_name="pdfs",
        azure_sql_database_url="mssql+aioodbc://user:pass@host/db",
        _env_file=None,
    )

    with patch("app.storage.azure.BlobServiceClient"):
        storage = create_file_storage(settings)

    assert storage.__class__.__name__ == "AzureBlobStorage"


def test_factory_uses_get_settings_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")

    storage = create_file_storage()

    assert isinstance(storage, LocalFileStorage)


def test_settings_rejects_unknown_app_env() -> None:
    with pytest.raises(ValueError, match="Unknown APP_ENV"):
        Settings(app_env="staging", _env_file=None)
