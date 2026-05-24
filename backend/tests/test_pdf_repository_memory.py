import pytest
from app.pdf_repository.memory import InMemoryPdfRepository


@pytest.mark.asyncio
async def test_create_returns_metadata_record() -> None:
    store = InMemoryPdfRepository()

    record = await store.create(
        filename="report.pdf",
        storage_key="pdfs/abc-report.pdf",
        size_bytes=42,
    )

    assert record.filename == "report.pdf"
    assert record.storage_key == "pdfs/abc-report.pdf"
    assert record.size_bytes == 42
    assert await store.get(record.id) == record


@pytest.mark.asyncio
async def test_init_and_close_are_no_ops() -> None:
    store = InMemoryPdfRepository()

    await store.init()
    await store.close()
