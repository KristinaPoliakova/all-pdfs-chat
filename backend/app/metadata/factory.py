from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.db.azure_sql import resolve_prod_database_url
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
        return resolve_prod_database_url(
            azure_sql_connectionstring=cfg.azure_sql_connectionstring,
        )
    return cfg.database_url


async def reset_metadata_store_state() -> None:
    global _store
    if _store is not None:
        await _store.close()
    _store = None
