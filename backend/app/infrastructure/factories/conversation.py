from __future__ import annotations

from app.application.ports.conversation import ConversationRepository
from app.config.settings import Settings
from app.infrastructure.persistence.sql.lifecycle import get_database
from app.infrastructure.persistence.sql.repositories.conversation import SqlConversationRepository


def create_conversation_repository(settings: Settings | None = None) -> ConversationRepository:
    """Dev/prod SQL store. Tests inject InMemoryConversationRepository via overrides."""
    return SqlConversationRepository(get_database(settings).session_factory)
