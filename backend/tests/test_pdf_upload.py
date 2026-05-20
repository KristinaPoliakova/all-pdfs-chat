from __future__ import annotations

import uuid

import pytest
from app.classification.types import PdfProcessingStatus
from app.config.settings import get_settings
from app.metadata.memory import InMemoryPdfMetadataStore
from app.storage.memory import InMemoryFileStorage
from httpx import AsyncClient

from tests.pdf_fixtures import make_text_pdf_bytes

PDF_BYTES = b"%PDF-1.4\n" + b"0" * 55
OVERSIZED_BYTES = b"x" * 101


@pytest.mark.asyncio
async def test_upload_pdf_returns_metadata_and_stores_file(
    api_client: AsyncClient,
    file_storage: InMemoryFileStorage,
    pdf_metadata_store: InMemoryPdfMetadataStore,
) -> None:
    pdf_bytes = make_text_pdf_bytes()
    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "report.pdf"
    assert body["size_bytes"] == len(pdf_bytes)
    assert body["processing_status"] == PdfProcessingStatus.CLASSIFIED.value
    assert len(body["pages"]) >= 1
    assert "storage_key" not in body
    uuid.UUID(body["id"])

    record = await pdf_metadata_store.get(body["id"])
    assert record is not None
    assert record.filename == "report.pdf"
    assert record.storage_key.startswith("pdfs/")
    assert file_storage.download(record.storage_key) == pdf_bytes
    assert record.size_bytes == len(pdf_bytes)


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf_content_type(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 415
    assert "pdf" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejects_file_exceeding_max_size(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "100")
    get_settings.cache_clear()

    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("big.pdf", OVERSIZED_BYTES, "application/pdf")},
    )

    assert response.status_code == 413
    assert "size" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejects_too_small_pdf(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("tiny.pdf", b"%PDF", "application/pdf")},
    )

    assert response.status_code == 400
    assert "small" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejects_missing_file(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/pdfs")

    assert response.status_code == 422
