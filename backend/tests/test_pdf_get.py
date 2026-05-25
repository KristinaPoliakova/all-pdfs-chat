from __future__ import annotations

import uuid

import pytest
from app.classification.types import PdfProcessingStatus
from httpx import AsyncClient

from tests.pdf_fixtures import make_text_pdf_bytes

PDF_BYTES = b"%PDF-1.4\n" + b"0" * 55


@pytest.mark.asyncio
async def test_upload_includes_location_header(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    pdf_bytes = make_text_pdf_bytes()

    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"/api/v1/pdfs/{body['id']}"


@pytest.mark.asyncio
async def test_get_pdf_returns_document_metadata(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
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

    response = await api_client.get(f"/api/v1/pdfs/{pdf_id}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == pdf_id
    assert body["filename"] == "report.pdf"
    assert body["processing_status"] == PdfProcessingStatus.PARSED.value
    assert body["page_count"] == 2
    assert "storage_key" not in body
    assert "pages" not in body


@pytest.mark.asyncio
async def test_get_pdf_returns_404_for_unknown_id(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await api_client.get(f"/api/v1/pdfs/{uuid.uuid4()}", headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_pdf_pages_returns_page_classifications(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
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

    response = await api_client.get(f"/api/v1/pdfs/{pdf_id}/pages", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body["pages"]) == 2
    assert body["pages"][0]["page_number"] == 1
    assert body["pages"][0]["page_class"] in {
        "born_digital_simple",
        "born_digital_complex",
    }


@pytest.mark.asyncio
async def test_get_pdf_pages_returns_empty_when_classification_failed(
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

    response = await api_client.get(f"/api/v1/pdfs/{pdf_id}/pages", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["pages"] == []


@pytest.mark.asyncio
async def test_get_pdf_pages_returns_404_for_unknown_id(
    api_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await api_client.get(
        f"/api/v1/pdfs/{uuid.uuid4()}/pages",
        headers=auth_headers,
    )

    assert response.status_code == 404
