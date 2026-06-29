from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ConversationRecord:
    id: str
    user_id: str
    pdf_document_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationRepository(Protocol):
    async def create(self, *, user_id: str, pdf_document_id: str) -> ConversationRecord: ...

    async def get_for_user(self, conversation_id: str, user_id: str) -> ConversationRecord: ...

    async def list_for_pdf(
        self, pdf_document_id: str, user_id: str
    ) -> list[ConversationRecord]: ...

    async def rename(self, conversation_id: str, *, title: str) -> ConversationRecord: ...

    async def touch(self, conversation_id: str, *, title_if_unset: str) -> ConversationRecord: ...

    async def delete(self, conversation_id: str) -> None: ...
