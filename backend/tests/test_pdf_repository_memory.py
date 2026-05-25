import pytest
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository


@pytest.mark.asyncio
async def test_create_returns_metadata_record() -> None:
    store = InMemoryPdfRepository()

    record = await store.create(
        filename="report.pdf",
        storage_key="pdfs/abc-report.pdf",
        size_bytes=42,
        user_id="user-1",
    )

    assert record.filename == "report.pdf"
    assert record.storage_key == "pdfs/abc-report.pdf"
    assert record.size_bytes == 42
    assert record.user_id == "user-1"
    assert await store.get(record.id) == record


@pytest.mark.asyncio
async def test_get_for_user_returns_record_for_owner() -> None:
    store = InMemoryPdfRepository()
    record = await store.create(
        filename="report.pdf",
        storage_key="pdfs/abc-report.pdf",
        size_bytes=42,
        user_id="user-1",
    )

    owned = await store.get_for_user(record.id, "user-1")

    assert owned == record


@pytest.mark.asyncio
async def test_get_for_user_raises_for_other_owner() -> None:
    store = InMemoryPdfRepository()
    record = await store.create(
        filename="report.pdf",
        storage_key="pdfs/abc-report.pdf",
        size_bytes=42,
        user_id="user-1",
    )

    with pytest.raises(LookupError):
        await store.get_for_user(record.id, "user-2")
