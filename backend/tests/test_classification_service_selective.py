from __future__ import annotations

from unittest.mock import patch

from app.classification.service import PdfClassificationService

from tests.pdf_fixtures import make_text_pdf_bytes
from tests.settings_helpers import make_test_settings


def test_classify_bytes_runs_pdfplumber_only_for_borderline_pages() -> None:
    service = PdfClassificationService(settings=make_test_settings(classification_max_pages=10))
    data = make_text_pdf_bytes(pages=2)
    seen_page_numbers: list[list[int] | None] = []

    def _capture_pdfplumber(_data: bytes, *, page_numbers: list[int] | None = None):
        seen_page_numbers.append(page_numbers)
        return {}

    with patch(
        "app.classification.service.extract_pdfplumber_page_features",
        side_effect=_capture_pdfplumber,
    ):
        service.classify_bytes(data)

    assert seen_page_numbers == [[1, 2]]


def test_classify_bytes_skips_pdfplumber_for_definitely_complex_pages() -> None:
    service = PdfClassificationService(settings=make_test_settings(classification_max_pages=10))
    data = make_text_pdf_bytes(pages=2)
    seen_page_numbers: list[list[int] | None] = []

    def _capture_pdfplumber(_data: bytes, *, page_numbers: list[int] | None = None):
        seen_page_numbers.append(page_numbers)
        return {}

    with (
        patch(
            "app.classification.service.is_definitely_complex_from_pymupdf",
            side_effect=[True, False],
        ),
        patch(
            "app.classification.service.extract_pdfplumber_page_features",
            side_effect=_capture_pdfplumber,
        ),
    ):
        service.classify_bytes(data)

    assert seen_page_numbers == [[2]]
