from __future__ import annotations

import pytest
from app.classification.service import PdfClassificationError, PdfClassificationService
from app.classification.types import PageClass
from app.config.settings import Settings

from tests.pdf_fixtures import make_text_pdf_bytes


def test_classify_bytes_returns_per_page_results() -> None:
    service = PdfClassificationService(settings=Settings(classification_max_pages=10))
    data = make_text_pdf_bytes(pages=2)

    results = service.classify_bytes(data)

    assert len(results) == 2
    assert results[0].page_number == 1
    assert results[1].page_number == 2
    assert results[0].page_class in {PageClass.BORN_DIGITAL_SIMPLE, PageClass.BORN_DIGITAL_COMPLEX}


def test_classify_bytes_rejects_pdf_exceeding_max_pages() -> None:
    service = PdfClassificationService(settings=Settings(classification_max_pages=1))
    data = make_text_pdf_bytes(pages=2)

    with pytest.raises(PdfClassificationError, match="page count"):
        service.classify_bytes(data)
