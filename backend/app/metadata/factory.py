from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.metadata.protocol import PdfMetadataStore
from app.metadata.sql import SqlPdfMetadataStore

_store: PdfMetadataStore | None = None


def create_pdf_metadata_store(settings: Settings | None = None) -> PdfMetadataStore:
    """Dev/prod SQL store. Tests inject InMemoryPdfMetadataStore via FastAPI overrides."""
    global _store
    if settings is not None:
        return SqlPdfMetadataStore(_database_url_for(cfg=settings))

    if _store is None:
        _store = SqlPdfMetadataStore(_database_url_for(cfg=get_settings()))
    return _store


def _database_url_for(*, cfg: Settings) -> str:
    if cfg.is_prod:
        if not cfg.azure_sql_database_url.strip():
            raise ValueError("AZURE_SQL_DATABASE_URL is required when APP_ENV=prod")
        return cfg.azure_sql_database_url
    return cfg.database_url


async def reset_metadata_store_state() -> None:
    global _store
    if _store is not None:
        await _store.close()
    _store = None
