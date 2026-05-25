from __future__ import annotations

from app.application.ports.sessions import SessionRepository
from app.config.settings import Settings
from app.infrastructure.persistence.sql.lifecycle import get_database
from app.infrastructure.persistence.sql.repositories.sessions import SqlSessionRepository

_store: SessionRepository | None = None


def create_session_repository(settings: Settings | None = None) -> SessionRepository:
    """Dev/prod SQL store. Tests inject InMemorySessionRepository via FastAPI overrides."""
    global _store
    if settings is not None:
        return SqlSessionRepository(get_database(settings).session_factory)

    if _store is None:
        _store = SqlSessionRepository(get_database().session_factory)
    return _store


async def reset_session_repository_state() -> None:
    global _store
    _store = None
