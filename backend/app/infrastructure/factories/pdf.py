from __future__ import annotations

from app.application.ports.pdf import PdfRepository
from app.config.settings import Settings
from app.infrastructure.persistence.sql.lifecycle import get_database
from app.infrastructure.persistence.sql.repositories.pdf import SqlPdfRepository


def create_pdf_repository(settings: Settings | None = None) -> PdfRepository:
    """Dev/prod SQL store. Tests inject InMemoryPdfRepository via FastAPI overrides."""
    return SqlPdfRepository(get_database(settings).session_factory)
