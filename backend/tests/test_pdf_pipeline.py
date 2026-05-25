from __future__ import annotations

import pytest
from app.classification.service import PdfClassificationService
from app.classification.types import PageClass, PageClassificationResult, PdfProcessingStatus
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository
from app.infrastructure.storage.memory import InMemoryFileStorage
from app.parsing.composite import CompositeDocumentParser
from app.parsing.types import PageExtract
from app.worker.pdf_pipeline import PdfProcessingPipeline

from tests.pdf_fixtures import make_text_pdf_bytes
from tests.settings_helpers import make_test_settings


class _FailingClassifier:
    def classify_bytes(self, data: bytes) -> list[PageClassificationResult]:
        msg = "broken pdf"
        raise ValueError(msg)


@pytest.mark.asyncio
async def test_pipeline_classifies_pdf_and_sets_classified() -> None:
    pdf_repository = InMemoryPdfRepository()
    file_storage = InMemoryFileStorage()
    settings = make_test_settings(classification_enabled=True, parsing_enabled=False)
    data = make_text_pdf_bytes(pages=2)
    storage_key = "pdfs/test.pdf"
    file_storage.upload(storage_key, data)
    record = await pdf_repository.create(
        user_id="user-1",
        filename="t.pdf",
        storage_key=storage_key,
        size_bytes=len(data),
    )
    pipeline = PdfProcessingPipeline(
        pdf_repository=pdf_repository,
        storage=file_storage,
        settings=settings,
        classifier=PdfClassificationService(settings=settings),
        parser=CompositeDocumentParser(settings=settings),
    )

    await pipeline.run(record.id)

    updated = await pdf_repository.get(record.id)
    assert updated.processing_status == PdfProcessingStatus.PARSED
    pages = await pdf_repository.get_pages(record.id)
    assert len(pages) == 2


@pytest.mark.asyncio
async def test_pipeline_extracts_simple_pages_locally() -> None:
    pdf_repository = InMemoryPdfRepository()
    file_storage = InMemoryFileStorage()
    settings = make_test_settings(classification_enabled=True, parsing_enabled=False)
    data = make_text_pdf_bytes(pages=1, text="Local extract me")
    storage_key = "pdfs/simple.pdf"
    file_storage.upload(storage_key, data)
    record = await pdf_repository.create(
        user_id="user-1",
        filename="simple.pdf",
        storage_key=storage_key,
        size_bytes=len(data),
    )
    await pdf_repository.save_page_classifications(
        record.id,
        [
            PageClassificationResult(
                page_number=1,
                page_class=PageClass.BORN_DIGITAL_SIMPLE,
                confidence=0.9,
            ),
        ],
        page_count=1,
        classified_at=record.created_at,
    )
    await pdf_repository.set_processing_status(record.id, PdfProcessingStatus.CLASSIFIED)
    pipeline = PdfProcessingPipeline(
        pdf_repository=pdf_repository,
        storage=file_storage,
        settings=settings,
        classifier=PdfClassificationService(settings=settings),
        parser=CompositeDocumentParser(settings=settings),
    )

    await pipeline._phase_parse(record.id, data)

    extracts = await pdf_repository.get_page_extracts(record.id)
    assert len(extracts) == 1
    assert extracts[0].extractor == "local_pymupdf"
    assert "Local extract me" in extracts[0].content_text


@pytest.mark.asyncio
async def test_pipeline_classification_failure_leaves_no_pages() -> None:
    pdf_repository = InMemoryPdfRepository()
    file_storage = InMemoryFileStorage()
    settings = make_test_settings(classification_enabled=True)
    data = make_text_pdf_bytes(pages=1)
    storage_key = "pdfs/fail.pdf"
    file_storage.upload(storage_key, data)
    record = await pdf_repository.create(
        user_id="user-1",
        filename="fail.pdf",
        storage_key=storage_key,
        size_bytes=len(data),
    )
    pipeline = PdfProcessingPipeline(
        pdf_repository=pdf_repository,
        storage=file_storage,
        settings=settings,
        classifier=_FailingClassifier(),  # type: ignore[arg-type]
        parser=CompositeDocumentParser(settings=settings),
    )

    await pipeline.run(record.id)

    updated = await pdf_repository.get(record.id)
    assert updated.processing_status == PdfProcessingStatus.CLASSIFICATION_FAILED
    assert await pdf_repository.get_pages(record.id) == []


@pytest.mark.asyncio
async def test_pipeline_uses_azure_parser_for_complex_pages() -> None:
    pdf_repository = InMemoryPdfRepository()
    file_storage = InMemoryFileStorage()
    settings = make_test_settings(classification_enabled=True, parsing_enabled=True)

    class _FakeAzure:
        async def parse_pages(
            self,
            pdf_bytes: bytes,
            *,
            page_numbers: list[int],
        ) -> list[PageExtract]:
            return [
                PageExtract(
                    page_number=page_number,
                    content_text=f"azure-{page_number}",
                    extractor="azure_document_intelligence",
                )
                for page_number in page_numbers
            ]

    data = make_text_pdf_bytes(pages=2)
    storage_key = "pdfs/complex.pdf"
    file_storage.upload(storage_key, data)
    record = await pdf_repository.create(
        user_id="user-1",
        filename="complex.pdf",
        storage_key=storage_key,
        size_bytes=len(data),
    )
    await pdf_repository.save_page_classifications(
        record.id,
        [
            PageClassificationResult(
                page_number=1,
                page_class=PageClass.BORN_DIGITAL_SIMPLE,
                confidence=0.9,
            ),
            PageClassificationResult(
                page_number=2,
                page_class=PageClass.BORN_DIGITAL_COMPLEX,
                confidence=0.9,
            ),
        ],
        page_count=2,
        classified_at=record.created_at,
    )
    await pdf_repository.set_processing_status(record.id, PdfProcessingStatus.CLASSIFIED)

    pipeline = PdfProcessingPipeline(
        pdf_repository=pdf_repository,
        storage=file_storage,
        settings=settings,
        classifier=PdfClassificationService(settings=settings),
        parser=CompositeDocumentParser(settings=settings, azure_parser=_FakeAzure()),
    )

    await pipeline._phase_parse(record.id, data)

    extracts = await pdf_repository.get_page_extracts(record.id)
    assert len(extracts) == 2
    by_page = {extract.page_number: extract for extract in extracts}
    assert by_page[1].extractor == "local_pymupdf"
    assert by_page[2].extractor == "azure_document_intelligence"
    assert by_page[2].content_text == "azure-2"
