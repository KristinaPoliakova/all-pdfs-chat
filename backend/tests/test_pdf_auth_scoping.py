from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.auth_helpers import register_and_get_auth_headers
from tests.pdf_fixtures import make_text_pdf_bytes


@pytest.mark.asyncio
async def test_upload_without_auth_returns_401(api_client: AsyncClient) -> None:
    pdf_bytes = make_text_pdf_bytes()

    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_with_auth_stores_user_id(
    api_client: AsyncClient,
    pdf_repository: object,
) -> None:
    headers = await register_and_get_auth_headers(api_client, email="owner@example.com")
    pdf_bytes = make_text_pdf_bytes()

    response = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )

    assert response.status_code == 201
    pdf_id = response.json()["id"]
    record = await pdf_repository.get(pdf_id)  # type: ignore[attr-defined]
    me = await api_client.get("/api/v1/auth/me", headers=headers)
    assert record.user_id == me.json()["id"]


@pytest.mark.asyncio
async def test_get_pdf_returns_404_for_other_users_document(api_client: AsyncClient) -> None:
    owner_headers = await register_and_get_auth_headers(api_client, email="owner@example.com")
    other_headers = await register_and_get_auth_headers(api_client, email="other@example.com")
    pdf_bytes = make_text_pdf_bytes()

    upload = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        headers=owner_headers,
    )
    pdf_id = upload.json()["id"]

    response = await api_client.get(f"/api/v1/pdfs/{pdf_id}", headers=other_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_pdf_pages_returns_404_for_other_users_document(
    api_client: AsyncClient,
) -> None:
    owner_headers = await register_and_get_auth_headers(api_client, email="pages-owner@example.com")
    other_headers = await register_and_get_auth_headers(api_client, email="pages-other@example.com")
    pdf_bytes = make_text_pdf_bytes()

    upload = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        headers=owner_headers,
    )
    pdf_id = upload.json()["id"]

    response = await api_client.get(f"/api/v1/pdfs/{pdf_id}/pages", headers=other_headers)

    assert response.status_code == 404
