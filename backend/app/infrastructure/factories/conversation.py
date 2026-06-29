from __future__ import annotations

from app.application.ports.conversation import ConversationRepository
from app.config.settings import Settings
from app.infrastructure.persistence.sql.lifecycle import get_database
from app.infrastructure.persistence.sql.repositories.conversation import SqlConversationRepository

_store: ConversationRepository | None = None


def create_conversation_repository(settings: Settings | None = None) -> ConversationRepository:
    """Dev/prod SQL store. Tests inject InMemoryConversationRepository via overrides."""
    global _store
    if settings is not None:
        return SqlConversationRepository(get_database(settings).session_factory)

    if _store is None:
        _store = SqlConversationRepository(get_database().session_factory)
    return _store


async def reset_conversation_repository_state() -> None:
    global _store
    _store = None
