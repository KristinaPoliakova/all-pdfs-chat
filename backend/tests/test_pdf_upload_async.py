from __future__ import annotations

import uuid

import pytest
from app.classification.types import PdfProcessingStatus
from app.config.settings import get_settings
from httpx import AsyncClient

from tests.pdf_fixtures import make_text_pdf_bytes

PDF_BYTES = b"%PDF-1.4\n" + b"0" * 55


@pytest.mark.asyncio
async def test_upload_returns_uploaded_without_pages_field(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
    drain_pdf_jobs: object,
) -> None:
    pdf_bytes = make_text_pdf_bytes(pages=2)
    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == PdfProcessingStatus.UPLOADED.value
    assert "pages" not in body
    uuid.UUID(body["id"])


@pytest.mark.asyncio
async def test_upload_then_worker_classifies_pages(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
    pdf_repository: object,
    job_queue: object,
    drain_pdf_jobs: object,
) -> None:
    pdf_bytes = make_text_pdf_bytes(pages=2)
    upload = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers,
    )
    pdf_id = upload.json()["id"]

    await drain_pdf_jobs()

    doc = await api_client.get(f"/api/v1/pdfs/{pdf_id}", headers=auth_headers)
    assert doc.json()["processing_status"] == PdfProcessingStatus.PARSED.value
    pages = await api_client.get(f"/api/v1/pdfs/{pdf_id}/pages", headers=auth_headers)
    assert len(pages.json()["pages"]) == 2


@pytest.mark.asyncio
async def test_upload_classification_failure_after_worker(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
    drain_pdf_jobs: object,
) -> None:
    upload = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("broken.pdf", PDF_BYTES, "application/pdf")},
        headers=auth_headers,
    )
    pdf_id = upload.json()["id"]

    await drain_pdf_jobs()

    doc = await api_client.get(f"/api/v1/pdfs/{pdf_id}", headers=auth_headers)
    assert doc.json()["processing_status"] == PdfProcessingStatus.CLASSIFICATION_FAILED.value
    pages = await api_client.get(f"/api/v1/pdfs/{pdf_id}/pages", headers=auth_headers)
    assert pages.json()["pages"] == []


@pytest.mark.asyncio
async def test_upload_skips_job_when_classification_disabled(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    job_queue: object,
) -> None:
    monkeypatch.setenv("CLASSIFICATION_ENABLED", "false")
    get_settings.cache_clear()

    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", make_text_pdf_bytes(), "application/pdf")},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["processing_status"] == PdfProcessingStatus.UPLOADED.value
    assert await job_queue.claim_next(worker_id="test") is None
