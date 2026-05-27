from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.classification.types import (
    PageClass,
    PageClassificationResult,
    PdfProcessingStatus,
)
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository

from tests.db_helpers import make_sql_pdf_repository, open_test_database, seed_sql_user_and_pdf


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
    store = InMemoryPdfRepository()

    record = await store.create(
        user_id="user-1",
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    assert record.processing_status == PdfProcessingStatus.UPLOADED
    assert record.page_count is None
    assert record.classified_at is None


@pytest.mark.asyncio
async def test_set_processing_status_updates_record() -> None:
    store = InMemoryPdfRepository()
    record = await store.create(
        user_id="user-1",
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
async def test_set_processing_status_parsing_failed_sets_parsing_error() -> None:
    store = InMemoryPdfRepository()
    record = await store.create(
        user_id="user-1",
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    await store.set_processing_status(
        record.id,
        PdfProcessingStatus.PARSING_FAILED,
        error="timeout",
    )
    updated = await store.get(record.id)

    assert updated.processing_status == PdfProcessingStatus.PARSING_FAILED
    assert updated.parsing_error == "timeout"
    assert updated.classification_error is None


@pytest.mark.asyncio
async def test_set_processing_status_parsed_sets_parsed_at() -> None:
    store = InMemoryPdfRepository()
    record = await store.create(
        user_id="user-1",
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    await store.set_processing_status(record.id, PdfProcessingStatus.PARSED)
    updated = await store.get(record.id)

    assert updated.processing_status == PdfProcessingStatus.PARSED
    assert updated.parsed_at is not None


@pytest.mark.asyncio
async def test_save_page_classifications_persists_pages() -> None:
    store = InMemoryPdfRepository()
    record = await store.create(
        user_id="user-1",
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
    store = InMemoryPdfRepository()
    record = await store.create(
        user_id="user-1",
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
    store = InMemoryPdfRepository()
    record = await store.create(
        user_id="user-1",
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    assert await store.get_pages(record.id) == []


@pytest.mark.asyncio
async def test_sql_store_persists_pages_and_status() -> None:
    runtime = await open_test_database()
    store = make_sql_pdf_repository(runtime)
    _user_id, pdf_id = await seed_sql_user_and_pdf(
        runtime,
        email="pages@example.com",
        storage_key="pdfs/pages-doc.pdf",
    )
    record = await store.get_for_user(pdf_id, _user_id)
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

    await runtime.close()


@pytest.mark.asyncio
async def test_set_processing_status_unknown_id_raises() -> None:
    store = InMemoryPdfRepository()

    with pytest.raises(LookupError):
        await store.set_processing_status(
            str(uuid.uuid4()),
            PdfProcessingStatus.CLASSIFIED,
        )
