from __future__ import annotations

import pytest
from app.application.ports.conversation_memory import ChatMessage
from app.application.services.conversation import (
    ConversationService,
    PdfNotReadyError,
    derive_conversation_title,
)
from app.classification.types import PdfProcessingStatus
from app.infrastructure.persistence.memory.conversation import InMemoryConversationRepository
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository


class _FakeMemory:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.messages: list[ChatMessage] = []

    async def get_messages(self, thread_id: str) -> list[ChatMessage]:
        return list(self.messages)

    async def delete_thread(self, thread_id: str) -> None:
        self.deleted.append(thread_id)


async def _make_parsed_pdf(pdfs: InMemoryPdfRepository, *, user_id: str = "u1") -> str:
    record = await pdfs.create(user_id=user_id, filename="d.pdf", storage_key="k", size_bytes=1)
    await pdfs.set_processing_status(record.id, PdfProcessingStatus.PARSED)
    return record.id


def test_derive_title_trims_and_truncates() -> None:
    assert derive_conversation_title("  hello   world  ") == "hello world"
    long = "word " * 40
    title = derive_conversation_title(long)
    assert len(title) <= 60
    assert title.endswith("\u2026")


@pytest.mark.asyncio
async def test_create_requires_parsed_pdf() -> None:
    pdfs = InMemoryPdfRepository()
    convs = InMemoryConversationRepository()
    service = ConversationService(repository=convs, memory=_FakeMemory(), pdf_repository=pdfs)
    unparsed = await pdfs.create(user_id="u1", filename="d.pdf", storage_key="k", size_bytes=1)

    with pytest.raises(PdfNotReadyError):
        await service.create(pdf_id=unparsed.id, user_id="u1")


@pytest.mark.asyncio
async def test_create_unknown_pdf_raises_lookup_error() -> None:
    service = ConversationService(
        repository=InMemoryConversationRepository(),
        memory=_FakeMemory(),
        pdf_repository=InMemoryPdfRepository(),
    )
    with pytest.raises(LookupError):
        await service.create(pdf_id="nope", user_id="u1")


@pytest.mark.asyncio
async def test_create_succeeds_for_parsed_pdf() -> None:
    pdfs = InMemoryPdfRepository()
    convs = InMemoryConversationRepository()
    service = ConversationService(repository=convs, memory=_FakeMemory(), pdf_repository=pdfs)
    pdf_id = await _make_parsed_pdf(pdfs)

    created = await service.create(pdf_id=pdf_id, user_id="u1")

    assert created.pdf_document_id == pdf_id
    assert created.title is None


@pytest.mark.asyncio
async def test_delete_deletes_memory_then_row() -> None:
    pdfs = InMemoryPdfRepository()
    convs = InMemoryConversationRepository()
    memory = _FakeMemory()
    service = ConversationService(repository=convs, memory=memory, pdf_repository=pdfs)
    pdf_id = await _make_parsed_pdf(pdfs)
    created = await service.create(pdf_id=pdf_id, user_id="u1")

    await service.delete(conversation_id=created.id, user_id="u1")

    assert memory.deleted == [created.id]
    with pytest.raises(LookupError):
        await convs.get_for_user(created.id, "u1")


@pytest.mark.asyncio
async def test_record_turn_sets_title_from_first_message_once() -> None:
    pdfs = InMemoryPdfRepository()
    convs = InMemoryConversationRepository()
    service = ConversationService(repository=convs, memory=_FakeMemory(), pdf_repository=pdfs)
    pdf_id = await _make_parsed_pdf(pdfs)
    created = await service.create(pdf_id=pdf_id, user_id="u1")

    await service.record_turn(conversation_id=created.id, first_message="What is the revenue?")
    await service.record_turn(conversation_id=created.id, first_message="second message ignored")

    assert (await convs.get_for_user(created.id, "u1")).title == "What is the revenue?"


@pytest.mark.asyncio
async def test_get_messages_checks_ownership() -> None:
    pdfs = InMemoryPdfRepository()
    convs = InMemoryConversationRepository()
    memory = _FakeMemory()
    memory.messages = [ChatMessage(role="user", content="hi", citations=[])]
    service = ConversationService(repository=convs, memory=memory, pdf_repository=pdfs)
    pdf_id = await _make_parsed_pdf(pdfs)
    created = await service.create(pdf_id=pdf_id, user_id="u1")

    assert await service.get_messages(conversation_id=created.id, user_id="u1") == memory.messages
    with pytest.raises(LookupError):
        await service.get_messages(conversation_id=created.id, user_id="intruder")


@pytest.mark.asyncio
async def test_get_pdf_for_chat_returns_conversation_and_pdf_for_parsed() -> None:
    pdfs = InMemoryPdfRepository()
    convs = InMemoryConversationRepository()
    service = ConversationService(repository=convs, memory=_FakeMemory(), pdf_repository=pdfs)
    pdf_id = await _make_parsed_pdf(pdfs)
    created = await service.create(pdf_id=pdf_id, user_id="u1")

    conversation, pdf = await service.get_pdf_for_chat(conversation_id=created.id, user_id="u1")

    assert conversation.id == created.id
    assert pdf.id == pdf_id


@pytest.mark.asyncio
async def test_get_pdf_for_chat_raises_pdf_not_ready_when_unparsed() -> None:
    pdfs = InMemoryPdfRepository()
    convs = InMemoryConversationRepository()
    service = ConversationService(repository=convs, memory=_FakeMemory(), pdf_repository=pdfs)
    # Create a parsed pdf + conversation, then regress status to simulate not-ready.
    record = await pdfs.create(user_id="u1", filename="d.pdf", storage_key="k", size_bytes=1)
    await pdfs.set_processing_status(record.id, PdfProcessingStatus.PARSED)
    created = await service.create(pdf_id=record.id, user_id="u1")
    await pdfs.set_processing_status(record.id, PdfProcessingStatus.UPLOADED)

    with pytest.raises(PdfNotReadyError):
        await service.get_pdf_for_chat(conversation_id=created.id, user_id="u1")


@pytest.mark.asyncio
async def test_get_pdf_for_chat_unknown_conversation_raises_lookup_error() -> None:
    service = ConversationService(
        repository=InMemoryConversationRepository(),
        memory=_FakeMemory(),
        pdf_repository=InMemoryPdfRepository(),
    )
    with pytest.raises(LookupError):
        await service.get_pdf_for_chat(conversation_id="nope", user_id="u1")
