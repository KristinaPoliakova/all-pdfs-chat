from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.conversation import ConversationRecord
from app.core.datetime_utils import ensure_utc
from app.infrastructure.persistence.sql.models.conversation import Conversation


class SqlConversationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, *, user_id: str, pdf_document_id: str) -> ConversationRecord:
        conversation = Conversation(user_id=user_id, pdf_document_id=pdf_document_id)
        async with self._session_factory() as session:
            try:
                session.add(conversation)
                await session.commit()
                await session.refresh(conversation)
            except Exception:
                await session.rollback()
                raise
        return _to_record(conversation)

    async def get_for_user(self, conversation_id: str, user_id: str) -> ConversationRecord:
        async with self._session_factory() as session:
            conversation = await session.get(Conversation, conversation_id)
            if conversation is None or conversation.user_id != user_id:
                raise LookupError(f"Conversation not found: {conversation_id}")
        return _to_record(conversation)

    async def list_for_pdf(self, pdf_document_id: str, user_id: str) -> list[ConversationRecord]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Conversation)
                .where(
                    Conversation.pdf_document_id == pdf_document_id,
                    Conversation.user_id == user_id,
                )
                .order_by(Conversation.updated_at.desc())
            )
            rows = result.scalars().all()
        return [_to_record(row) for row in rows]

    async def rename(self, conversation_id: str, *, title: str) -> ConversationRecord:
        async with self._session_factory() as session:
            conversation = await session.get(Conversation, conversation_id)
            if conversation is None:
                raise LookupError(f"Conversation not found: {conversation_id}")
            conversation.title = title
            conversation.updated_at = datetime.now(UTC)
            try:
                await session.commit()
                await session.refresh(conversation)
            except Exception:
                await session.rollback()
                raise
        return _to_record(conversation)

    async def touch(self, conversation_id: str, *, title_if_unset: str) -> ConversationRecord:
        async with self._session_factory() as session:
            conversation = await session.get(Conversation, conversation_id)
            if conversation is None:
                raise LookupError(f"Conversation not found: {conversation_id}")
            if conversation.title is None and title_if_unset:
                conversation.title = title_if_unset
            conversation.updated_at = datetime.now(UTC)
            try:
                await session.commit()
                await session.refresh(conversation)
            except Exception:
                await session.rollback()
                raise
        return _to_record(conversation)

    async def delete(self, conversation_id: str) -> None:
        async with self._session_factory() as session:
            try:
                await session.execute(
                    delete(Conversation).where(Conversation.id == conversation_id)
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise


def _to_record(conversation: Conversation) -> ConversationRecord:
    return ConversationRecord(
        id=conversation.id,
        user_id=conversation.user_id,
        pdf_document_id=conversation.pdf_document_id,
        title=conversation.title,
        created_at=ensure_utc(conversation.created_at),
        updated_at=ensure_utc(conversation.updated_at),
    )
