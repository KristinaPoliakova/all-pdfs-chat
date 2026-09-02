from __future__ import annotations

from app.application.ports.users import UserRepository
from app.config.settings import Settings
from app.infrastructure.persistence.sql.lifecycle import get_database
from app.infrastructure.persistence.sql.repositories.users import SqlUserRepository


def create_user_repository(settings: Settings | None = None) -> UserRepository:
    """Dev/prod SQL store. Tests inject InMemoryUserRepository via FastAPI overrides."""
    return SqlUserRepository(get_database(settings).session_factory)
