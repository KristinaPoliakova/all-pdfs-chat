from __future__ import annotations

import pytest
from app.classification.service import PdfClassificationError, PdfClassificationService
from app.classification.types import PageClass

from tests.pdf_fixtures import make_text_pdf_bytes
from tests.settings_helpers import make_test_settings


def test_classify_bytes_returns_per_page_results() -> None:
    service = PdfClassificationService(settings=make_test_settings(classification_max_pages=10))
    data = make_text_pdf_bytes(pages=2)

    output = service.classify_bytes(data)

    assert len(output.pages) == 2
    assert output.pages[0].page_number == 1
    assert output.pages[1].page_number == 2
    assert output.pages[0].page_class in {
        PageClass.BORN_DIGITAL_SIMPLE,
        PageClass.BORN_DIGITAL_COMPLEX,
    }
    assert 1 in output.page_text_by_number
    assert output.page_text_by_number[1]


def test_classify_bytes_rejects_pdf_exceeding_max_pages() -> None:
    service = PdfClassificationService(settings=make_test_settings(classification_max_pages=1))
    data = make_text_pdf_bytes(pages=2)

    with pytest.raises(PdfClassificationError, match="page count"):
        service.classify_bytes(data)


def test_classify_bytes_stores_extracted_text_for_each_page() -> None:
    service = PdfClassificationService(settings=make_test_settings(classification_max_pages=10))
    body = "Cached classification text for parsing reuse."
    data = make_text_pdf_bytes(pages=1, text=body)

    output = service.classify_bytes(data)

    assert body in output.page_text_by_number[1]
