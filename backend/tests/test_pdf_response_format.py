from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.pdf_fixtures import make_text_pdf_bytes


@pytest.mark.asyncio
async def test_upload_response_omits_null_fields_and_uses_utc_z(
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
    assert "pages" not in body
    assert "page_count" not in body
    assert "classification_error" not in body
    assert "classified_at" not in body
    assert "parsing_error" not in body
    assert "parsed_at" not in body
    assert body["created_at"].endswith("Z")
