from __future__ import annotations

from app.application.ports.storage import FileStorage
from app.config.settings import Settings, get_settings
from app.infrastructure.storage.azure import AzureBlobStorage
from app.infrastructure.storage.local import LocalFileStorage


def create_file_storage(settings: Settings | None = None) -> FileStorage:
    return _build_file_storage(settings or get_settings())


def _build_file_storage(cfg: Settings) -> FileStorage:
    if cfg.uses_local_storage:
        return LocalFileStorage(cfg.resolved_local_storage_path)

    return AzureBlobStorage(
        connection_string=cfg.azure_storage_connection_string,
        container_name=cfg.azure_storage_container_name,
    )
