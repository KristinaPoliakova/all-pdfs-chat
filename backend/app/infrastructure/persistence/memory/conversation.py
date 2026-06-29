from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime

from app.application.ports.conversation import ConversationRecord


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self._records: dict[str, ConversationRecord] = {}
        self._seq = 0

    def _now(self) -> datetime:
        # Monotonic-ish timestamps so ordering is deterministic in fast tests.
        self._seq += 1
        return datetime.now(UTC).replace(microsecond=self._seq % 1_000_000)

    async def create(self, *, user_id: str, pdf_document_id: str) -> ConversationRecord:
        now = self._now()
        record = ConversationRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            pdf_document_id=pdf_document_id,
            title=None,
            created_at=now,
            updated_at=now,
        )
        self._records[record.id] = record
        return record

    async def get_for_user(self, conversation_id: str, user_id: str) -> ConversationRecord:
        record = self._records.get(conversation_id)
        if record is None or record.user_id != user_id:
            raise LookupError(f"Conversation not found: {conversation_id}")
        return record

    async def list_for_pdf(self, pdf_document_id: str, user_id: str) -> list[ConversationRecord]:
        matches = [
            record
            for record in self._records.values()
            if record.pdf_document_id == pdf_document_id and record.user_id == user_id
        ]
        return sorted(matches, key=lambda r: r.updated_at, reverse=True)

    async def rename(self, conversation_id: str, *, title: str) -> ConversationRecord:
        record = self._require(conversation_id)
        updated = replace(record, title=title, updated_at=self._now())
        self._records[conversation_id] = updated
        return updated

    async def touch(self, conversation_id: str, *, title_if_unset: str) -> ConversationRecord:
        record = self._require(conversation_id)
        keep_existing = record.title is not None or not title_if_unset
        new_title = record.title if keep_existing else title_if_unset
        updated = replace(record, title=new_title, updated_at=self._now())
        self._records[conversation_id] = updated
        return updated

    async def delete(self, conversation_id: str) -> None:
        self._records.pop(conversation_id, None)

    def _require(self, conversation_id: str) -> ConversationRecord:
        record = self._records.get(conversation_id)
        if record is None:
            raise LookupError(f"Conversation not found: {conversation_id}")
        return record
