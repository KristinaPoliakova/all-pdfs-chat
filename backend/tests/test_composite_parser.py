from __future__ import annotations

from unittest.mock import patch

import pytest
from app.classification.types import PageClass, PageClassificationResult
from app.parsing.composite import CompositeDocumentParser
from app.parsing.types import PageExtract

from tests.settings_helpers import make_test_settings


@pytest.mark.asyncio
async def test_parse_document_uses_cached_text_for_simple_pages() -> None:
    settings = make_test_settings(parsing_enabled=False)
    parser = CompositeDocumentParser(settings=settings)
    pages = [
        PageClassificationResult(
            page_number=1,
            page_class=PageClass.BORN_DIGITAL_SIMPLE,
            confidence=0.9,
        ),
    ]

    with patch("app.parsing.composite.extract_page_text") as extract_page_text:
        extracts = await parser.parse_document(
            b"%PDF",
            pages,
            page_text_by_number={1: "Cached text"},
        )

    extract_page_text.assert_not_called()
    assert extracts == [
        PageExtract(
            page_number=1,
            content_text="Cached text",
            extractor="local_pymupdf",
        ),
    ]
