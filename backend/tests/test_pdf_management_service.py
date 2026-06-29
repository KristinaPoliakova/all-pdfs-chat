from __future__ import annotations

import pytest
from app.application.services.pdf_management import PdfManagementService
from app.infrastructure.persistence.memory.conversation import InMemoryConversationRepository
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository
from app.infrastructure.storage.memory import InMemoryFileStorage


class _FakeMemory:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def get_messages(self, thread_id: str):
        return []

    async def delete_thread(self, thread_id: str) -> None:
        self.deleted.append(thread_id)


def _make_service(
    pdfs: InMemoryPdfRepository,
    convs: InMemoryConversationRepository,
    memory: _FakeMemory,
    storage: InMemoryFileStorage,
) -> PdfManagementService:
    return PdfManagementService(
        pdf_repository=pdfs,
        conversation_repository=convs,
        memory=memory,
        storage=storage,
    )


@pytest.mark.asyncio
async def test_list_returns_only_my_pdfs() -> None:
    pdfs = InMemoryPdfRepository()
    await pdfs.create(user_id="u1", filename="a.pdf", storage_key="k1", size_bytes=1)
    await pdfs.create(user_id="u2", filename="b.pdf", storage_key="k2", size_bytes=1)
    service = _make_service(
        pdfs, InMemoryConversationRepository(), _FakeMemory(), InMemoryFileStorage()
    )

    listed = await service.list(user_id="u1")

    assert [r.filename for r in listed] == ["a.pdf"]


@pytest.mark.asyncio
async def test_rename_requires_ownership() -> None:
    pdfs = InMemoryPdfRepository()
    created = await pdfs.create(user_id="u1", filename="a.pdf", storage_key="k", size_bytes=1)
    service = _make_service(
        pdfs, InMemoryConversationRepository(), _FakeMemory(), InMemoryFileStorage()
    )

    with pytest.raises(LookupError):
        await service.rename(pdf_id=created.id, user_id="intruder", filename="x.pdf")

    renamed = await service.rename(pdf_id=created.id, user_id="u1", filename="x.pdf")
    assert renamed.filename == "x.pdf"


@pytest.mark.asyncio
async def test_delete_removes_threads_blob_and_pdf() -> None:
    pdfs = InMemoryPdfRepository()
    convs = InMemoryConversationRepository()
    memory = _FakeMemory()
    storage = InMemoryFileStorage()
    storage.upload("k", b"data")
    created = await pdfs.create(user_id="u1", filename="a.pdf", storage_key="k", size_bytes=4)
    c1 = await convs.create(user_id="u1", pdf_document_id=created.id)
    c2 = await convs.create(user_id="u1", pdf_document_id=created.id)
    service = _make_service(pdfs, convs, memory, storage)

    await service.delete(pdf_id=created.id, user_id="u1")

    assert set(memory.deleted) == {c1.id, c2.id}
    assert storage.exists("k") is False
    with pytest.raises(LookupError):
        await pdfs.get(created.id)


@pytest.mark.asyncio
async def test_delete_unknown_pdf_raises() -> None:
    service = _make_service(
        InMemoryPdfRepository(),
        InMemoryConversationRepository(),
        _FakeMemory(),
        InMemoryFileStorage(),
    )
    with pytest.raises(LookupError):
        await service.delete(pdf_id="nope", user_id="u1")
