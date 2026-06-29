from __future__ import annotations

from app.application.ports.conversation import ConversationRecord, ConversationRepository
from app.application.ports.conversation_memory import ChatMessage, ConversationMemoryPort
from app.application.ports.pdf import PdfRecord, PdfRepository
from app.classification.types import PdfProcessingStatus

_TITLE_MAX_LENGTH = 60


class PdfNotReadyError(Exception):
    """Raised when creating/using a conversation for a PDF that is not parsed."""


def derive_conversation_title(message: str, *, max_length: int = _TITLE_MAX_LENGTH) -> str:
    collapsed = " ".join(message.split())
    if len(collapsed) <= max_length:
        return collapsed
    return collapsed[: max_length - 1].rstrip() + "\u2026"


class ConversationService:
    def __init__(
        self,
        *,
        repository: ConversationRepository,
        memory: ConversationMemoryPort,
        pdf_repository: PdfRepository,
    ) -> None:
        self._repository = repository
        self._memory = memory
        self._pdf_repository = pdf_repository

    async def create(self, *, pdf_id: str, user_id: str) -> ConversationRecord:
        record = await self._pdf_repository.get_for_user(pdf_id, user_id)
        if record.processing_status != PdfProcessingStatus.PARSED:
            raise PdfNotReadyError("PDF is not ready for chat yet")
        return await self._repository.create(user_id=user_id, pdf_document_id=pdf_id)

    async def list_for_pdf(self, *, pdf_id: str, user_id: str) -> list[ConversationRecord]:
        await self._pdf_repository.get_for_user(pdf_id, user_id)
        return await self._repository.list_for_pdf(pdf_id, user_id)

    async def get(self, *, conversation_id: str, user_id: str) -> ConversationRecord:
        return await self._repository.get_for_user(conversation_id, user_id)

    async def get_pdf_for_chat(
        self, *, conversation_id: str, user_id: str
    ) -> tuple[ConversationRecord, PdfRecord]:
        conversation = await self._repository.get_for_user(conversation_id, user_id)
        pdf = await self._pdf_repository.get_for_user(conversation.pdf_document_id, user_id)
        if pdf.processing_status != PdfProcessingStatus.PARSED:
            raise PdfNotReadyError("PDF is not ready for chat yet")
        return conversation, pdf

    async def rename(self, *, conversation_id: str, user_id: str, title: str) -> ConversationRecord:
        await self._repository.get_for_user(conversation_id, user_id)
        return await self._repository.rename(conversation_id, title=title)

    async def delete(self, *, conversation_id: str, user_id: str) -> None:
        await self._repository.get_for_user(conversation_id, user_id)
        await self._memory.delete_thread(conversation_id)
        await self._repository.delete(conversation_id)

    async def get_messages(self, *, conversation_id: str, user_id: str) -> list[ChatMessage]:
        await self._repository.get_for_user(conversation_id, user_id)
        return await self._memory.get_messages(conversation_id)

    async def record_turn(self, *, conversation_id: str, first_message: str) -> None:
        await self._repository.touch(
            conversation_id, title_if_unset=derive_conversation_title(first_message)
        )
