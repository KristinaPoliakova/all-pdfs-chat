from __future__ import annotations

from app.application.ports.users import UserRepository
from app.config.settings import Settings
from app.infrastructure.persistence.sql.lifecycle import get_database
from app.infrastructure.persistence.sql.repositories.users import SqlUserRepository

_store: UserRepository | None = None


def create_user_repository(settings: Settings | None = None) -> UserRepository:
    """Dev/prod SQL store. Tests inject InMemoryUserRepository via FastAPI overrides."""
    global _store
    if settings is not None:
        return SqlUserRepository(get_database(settings).session_factory)

    if _store is None:
        _store = SqlUserRepository(get_database().session_factory)
    return _store


async def reset_user_repository_state() -> None:
    global _store
    _store = None
