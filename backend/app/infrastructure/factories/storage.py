from __future__ import annotations

from app.application.ports.storage import FileStorage
from app.config.settings import Settings, get_settings
from app.infrastructure.storage.azure import AzureBlobStorage
from app.infrastructure.storage.local import LocalFileStorage

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
    if cfg.uses_local_storage:
        return LocalFileStorage(cfg.resolved_local_storage_path)

    return AzureBlobStorage(
        connection_string=cfg.azure_storage_connection_string,
        container_name=cfg.azure_storage_container_name,
    )
