from __future__ import annotations

from app.application.ports.sessions import SessionRepository
from app.config.settings import Settings
from app.infrastructure.persistence.sql.lifecycle import get_database
from app.infrastructure.persistence.sql.repositories.sessions import SqlSessionRepository


def create_session_repository(settings: Settings | None = None) -> SessionRepository:
    """Dev/prod SQL store. Tests inject InMemorySessionRepository via FastAPI overrides."""
    return SqlSessionRepository(get_database(settings).session_factory)
