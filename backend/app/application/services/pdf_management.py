from __future__ import annotations

import logging

from app.application.ports.conversation import ConversationRepository
from app.application.ports.conversation_memory import ConversationMemoryPort
from app.application.ports.pdf import PdfRecord, PdfRepository
from app.application.ports.storage import FileStorage

logger = logging.getLogger(__name__)


class PdfManagementService:
    def __init__(
        self,
        *,
        pdf_repository: PdfRepository,
        conversation_repository: ConversationRepository,
        memory: ConversationMemoryPort,
        storage: FileStorage,
    ) -> None:
        self._pdf_repository = pdf_repository
        self._conversation_repository = conversation_repository
        self._memory = memory
        self._storage = storage

    async def list(self, *, user_id: str) -> list[PdfRecord]:
        return await self._pdf_repository.list_for_user(user_id)

    async def rename(self, *, pdf_id: str, user_id: str, filename: str) -> PdfRecord:
        await self._pdf_repository.get_for_user(pdf_id, user_id)
        return await self._pdf_repository.rename(pdf_id, filename=filename)

    async def delete(self, *, pdf_id: str, user_id: str) -> None:
        record = await self._pdf_repository.get_for_user(pdf_id, user_id)
        conversations = await self._conversation_repository.list_for_pdf(pdf_id, user_id)
        for conversation in conversations:
            await self._memory.delete_thread(conversation.id)
        await self._pdf_repository.delete(pdf_id)
        try:
            self._storage.delete(record.storage_key)
        except Exception:
            # Orphaned blob is harmless and retryable; never fail the delete on it.
            logger.warning("Failed to delete blob for pdf_id=%s", pdf_id, exc_info=True)
