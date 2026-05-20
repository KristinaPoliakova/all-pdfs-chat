from __future__ import annotations

import uuid

import pytest
from app.classification.types import PdfProcessingStatus
from app.config.settings import get_settings
from app.metadata.memory import InMemoryPdfMetadataStore
from httpx import AsyncClient

from tests.pdf_fixtures import make_text_pdf_bytes

PDF_BYTES = b"%PDF-1.4\n" + b"0" * 55


@pytest.mark.asyncio
async def test_upload_classifies_pages_and_returns_201(
    api_client: AsyncClient,
    pdf_metadata_store: InMemoryPdfMetadataStore,
) -> None:
    pdf_bytes = make_text_pdf_bytes(pages=2)

    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == PdfProcessingStatus.CLASSIFIED.value
    assert body["page_count"] == 2
    assert len(body["pages"]) == 2
    assert body["pages"][0]["page_number"] == 1
    assert body["pages"][0]["page_class"] in {
        "born_digital_simple",
        "born_digital_complex",
    }

    record = await pdf_metadata_store.get(body["id"])
    assert record is not None
    assert record.processing_status == PdfProcessingStatus.CLASSIFIED
    pages = await pdf_metadata_store.get_pages(body["id"])
    assert len(pages) == 2


@pytest.mark.asyncio
async def test_upload_returns_201_with_classification_failed_for_unparseable_pdf(
    api_client: AsyncClient,
    pdf_metadata_store: InMemoryPdfMetadataStore,
) -> None:
    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("broken.pdf", PDF_BYTES, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == PdfProcessingStatus.CLASSIFICATION_FAILED.value
    assert body["pages"] == []
    assert body["page_count"] is None

    record = await pdf_metadata_store.get(body["id"])
    assert record is not None
    assert record.classification_error
    assert await pdf_metadata_store.get_pages(body["id"]) == []


@pytest.mark.asyncio
async def test_upload_skips_classification_when_disabled(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLASSIFICATION_ENABLED", "false")
    get_settings.cache_clear()
    pdf_bytes = make_text_pdf_bytes()

    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == PdfProcessingStatus.UPLOADED.value
    assert body["pages"] == []
    uuid.UUID(body["id"])
