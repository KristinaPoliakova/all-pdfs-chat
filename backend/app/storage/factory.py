from __future__ import annotations

from app.config.settings import LOCAL_STORAGE_PATH, Settings, get_settings
from app.storage.azure import AzureBlobStorage
from app.storage.local import LocalFileStorage
from app.storage.protocol import FileStorage

_storage: FileStorage | None = None


def create_file_storage(settings: Settings | None = None) -> FileStorage:
    if settings is not None:
        return _build_file_storage(settings)

    global _storage
    if _storage is None:
        _storage = _build_file_storage(get_settings())
    return _storage


def reset_file_storage_state() -> None:
    global _storage
    _storage = None


def _build_file_storage(cfg: Settings) -> FileStorage:
    if cfg.is_prod:
        return AzureBlobStorage(
            connection_string=cfg.azure_storage_connection_string,
            container_name=cfg.azure_storage_container_name,
        )

    return LocalFileStorage(LOCAL_STORAGE_PATH)
