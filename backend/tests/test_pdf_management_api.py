from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.pdf_fixtures import make_text_pdf_bytes


async def _upload(api_client: AsyncClient, auth_headers) -> str:
    upload = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", make_text_pdf_bytes(pages=1), "application/pdf")},
        headers=auth_headers,
    )
    return upload.json()["id"]


@pytest.mark.asyncio
async def test_list_pdfs_returns_only_mine(api_client: AsyncClient, auth_headers) -> None:
    pdf_id = await _upload(api_client, auth_headers)

    resp = await api_client.get("/api/v1/pdfs", headers=auth_headers)
    assert resp.status_code == 200
    assert [p["id"] for p in resp.json()] == [pdf_id]


@pytest.mark.asyncio
async def test_rename_pdf(api_client: AsyncClient, auth_headers) -> None:
    pdf_id = await _upload(api_client, auth_headers)

    resp = await api_client.patch(
        f"/api/v1/pdfs/{pdf_id}", json={"filename": "renamed.pdf"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["filename"] == "renamed.pdf"


@pytest.mark.asyncio
async def test_delete_pdf(api_client: AsyncClient, auth_headers) -> None:
    pdf_id = await _upload(api_client, auth_headers)

    resp = await api_client.delete(f"/api/v1/pdfs/{pdf_id}", headers=auth_headers)
    assert resp.status_code == 204

    missing = await api_client.get(f"/api/v1/pdfs/{pdf_id}", headers=auth_headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_list_requires_auth(api_client: AsyncClient) -> None:
    resp = await api_client.get("/api/v1/pdfs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_unknown_pdf_returns_404(api_client: AsyncClient, auth_headers) -> None:
    resp = await api_client.delete(f"/api/v1/pdfs/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
