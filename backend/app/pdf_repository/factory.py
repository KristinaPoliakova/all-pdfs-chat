from __future__ import annotations

from app.config.settings import Settings
from app.db.lifecycle import get_database
from app.db.repositories.pdf import SqlPdfRepository
from app.pdf_repository.protocol import PdfRepository

_store: PdfRepository | None = None


def create_pdf_repository(settings: Settings | None = None) -> PdfRepository:
    """Dev/prod SQL store. Tests inject InMemoryPdfRepository via FastAPI overrides."""
    global _store
    if settings is not None:
        return SqlPdfRepository(get_database(settings).session_factory)

    if _store is None:
        _store = SqlPdfRepository(get_database().session_factory)
    return _store


async def reset_pdf_repository_state() -> None:
    global _store
    _store = None
