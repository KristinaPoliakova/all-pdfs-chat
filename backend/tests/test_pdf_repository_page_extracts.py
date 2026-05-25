from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.classification.types import PageClass, PageClassificationResult
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository
from app.parsing.types import PageExtract

from tests.db_helpers import make_sql_pdf_repository, open_test_database


def _page_result(page_number: int, *, page_class: PageClass) -> PageClassificationResult:
    return PageClassificationResult(
        page_number=page_number,
        page_class=page_class,
        confidence=0.9,
    )


@pytest.mark.asyncio
async def test_save_page_extracts_persists_content() -> None:
    store = InMemoryPdfRepository()
    record = await store.create(
        user_id="user-1",
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )
    await store.save_page_classifications(
        record.id,
        [_page_result(1, page_class=PageClass.BORN_DIGITAL_SIMPLE)],
        page_count=1,
        classified_at=datetime.now(UTC),
    )

    await store.save_page_extracts(
        record.id,
        [
            PageExtract(
                page_number=1,
                content_text="Hello world",
                extractor="local_pymupdf",
            ),
        ],
    )

    extracts = await store.get_page_extracts(record.id)
    assert len(extracts) == 1
    assert extracts[0].page_number == 1
    assert extracts[0].content_text == "Hello world"
    assert extracts[0].extractor == "local_pymupdf"


@pytest.mark.asyncio
async def test_save_page_extracts_replaces_existing_rows() -> None:
    store = InMemoryPdfRepository()
    record = await store.create(
        user_id="user-1",
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )
    await store.save_page_classifications(
        record.id,
        [_page_result(1, page_class=PageClass.BORN_DIGITAL_SIMPLE)],
        page_count=1,
        classified_at=datetime.now(UTC),
    )
    await store.save_page_extracts(
        record.id,
        [PageExtract(page_number=1, content_text="first", extractor="local_pymupdf")],
    )

    await store.save_page_extracts(
        record.id,
        [
            PageExtract(
                page_number=1,
                content_text="second",
                extractor="azure_document_intelligence",
            ),
        ],
    )

    extracts = await store.get_page_extracts(record.id)
    assert len(extracts) == 1
    assert extracts[0].content_text == "second"
    assert extracts[0].extractor == "azure_document_intelligence"


@pytest.mark.asyncio
async def test_sql_store_persists_page_extracts() -> None:
    runtime = await open_test_database()
    store = make_sql_pdf_repository(runtime)
    record = await store.create(
        user_id="user-1",
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )
    await store.save_page_classifications(
        record.id,
        [_page_result(1, page_class=PageClass.BORN_DIGITAL_SIMPLE)],
        page_count=1,
        classified_at=datetime.now(UTC),
    )
    await store.save_page_extracts(
        record.id,
        [PageExtract(page_number=1, content_text="sql text", extractor="local_pymupdf")],
    )

    extracts = await store.get_page_extracts(record.id)
    assert len(extracts) == 1
    assert extracts[0].content_text == "sql text"

    await runtime.close()
