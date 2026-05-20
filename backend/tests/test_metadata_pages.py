from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.classification.types import (
    PageClass,
    PageClassificationResult,
    PdfProcessingStatus,
)
from app.metadata.memory import InMemoryPdfMetadataStore
from app.metadata.sql import SqlPdfMetadataStore


def _page_result(
    page_number: int,
    *,
    page_class: PageClass = PageClass.BORN_DIGITAL_SIMPLE,
    confidence: float = 0.9,
) -> PageClassificationResult:
    return PageClassificationResult(
        page_number=page_number,
        page_class=page_class,
        confidence=confidence,
    )


@pytest.mark.asyncio
async def test_create_defaults_processing_status_to_uploaded() -> None:
    store = InMemoryPdfMetadataStore()

    record = await store.create(
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    assert record.processing_status == PdfProcessingStatus.UPLOADED
    assert record.page_count is None
    assert record.classified_at is None


@pytest.mark.asyncio
async def test_set_processing_status_updates_record() -> None:
    store = InMemoryPdfMetadataStore()
    record = await store.create(
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    await store.set_processing_status(
        record.id,
        PdfProcessingStatus.CLASSIFICATION_FAILED,
        error="timeout",
    )
    updated = await store.get(record.id)

    assert updated is not None
    assert updated.processing_status == PdfProcessingStatus.CLASSIFICATION_FAILED
    assert updated.classification_error == "timeout"


@pytest.mark.asyncio
async def test_save_page_classifications_persists_pages() -> None:
    store = InMemoryPdfMetadataStore()
    record = await store.create(
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )
    pages = [
        _page_result(1, page_class=PageClass.BORN_DIGITAL_SIMPLE),
        _page_result(2, page_class=PageClass.BORN_DIGITAL_COMPLEX, confidence=0.95),
    ]

    await store.save_page_classifications(
        record.id,
        pages,
        page_count=2,
        classified_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
    )
    await store.set_processing_status(record.id, PdfProcessingStatus.CLASSIFIED)

    saved = await store.get_pages(record.id)
    updated = await store.get(record.id)

    assert len(saved) == 2
    assert saved[0].page_number == 1
    assert saved[0].page_class == PageClass.BORN_DIGITAL_SIMPLE
    assert saved[1].page_class == PageClass.BORN_DIGITAL_COMPLEX
    assert updated is not None
    assert updated.page_count == 2
    assert updated.processing_status == PdfProcessingStatus.CLASSIFIED
    assert updated.classified_at == datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_save_page_classifications_replaces_existing_pages() -> None:
    store = InMemoryPdfMetadataStore()
    record = await store.create(
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )
    await store.save_page_classifications(
        record.id,
        [_page_result(1)],
        page_count=1,
        classified_at=datetime.now(UTC),
    )

    await store.save_page_classifications(
        record.id,
        [_page_result(1, page_class=PageClass.BORN_DIGITAL_COMPLEX)],
        page_count=1,
        classified_at=datetime.now(UTC),
    )

    saved = await store.get_pages(record.id)
    assert len(saved) == 1
    assert saved[0].page_class == PageClass.BORN_DIGITAL_COMPLEX


@pytest.mark.asyncio
async def test_get_pages_returns_empty_for_document_without_pages() -> None:
    store = InMemoryPdfMetadataStore()
    record = await store.create(
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    assert await store.get_pages(record.id) == []


@pytest.mark.asyncio
async def test_sql_store_persists_pages_and_status() -> None:
    store = SqlPdfMetadataStore("sqlite+aiosqlite:///:memory:")
    await store.init()

    record = await store.create(
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )
    await store.save_page_classifications(
        record.id,
        [_page_result(1)],
        page_count=1,
        classified_at=datetime.now(UTC),
    )
    await store.set_processing_status(record.id, PdfProcessingStatus.CLASSIFIED)

    saved = await store.get_pages(record.id)
    assert len(saved) == 1
    assert saved[0].page_class == PageClass.BORN_DIGITAL_SIMPLE

    await store.close()


@pytest.mark.asyncio
async def test_set_processing_status_unknown_id_raises() -> None:
    store = InMemoryPdfMetadataStore()

    with pytest.raises(LookupError):
        await store.set_processing_status(
            str(uuid.uuid4()),
            PdfProcessingStatus.CLASSIFIED,
        )
