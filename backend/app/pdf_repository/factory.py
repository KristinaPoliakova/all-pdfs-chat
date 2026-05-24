from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.db.database_url import database_url_for
from app.db.repositories.pdf import SqlPdfRepository
from app.pdf_repository.protocol import PdfRepository

_store: PdfRepository | None = None


def create_pdf_repository(settings: Settings | None = None) -> PdfRepository:
    """Dev/prod SQL store. Tests inject InMemoryPdfRepository via FastAPI overrides."""
    global _store
    if settings is not None:
        return SqlPdfRepository(database_url_for(cfg=settings))

    if _store is None:
        _store = SqlPdfRepository(database_url_for(cfg=get_settings()))
    return _store


async def reset_pdf_repository_state() -> None:
    global _store
    if _store is not None:
        await _store.close()
    _store = None
