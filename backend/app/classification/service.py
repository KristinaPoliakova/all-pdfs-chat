from __future__ import annotations

from app.classification.pdfplumber_features import extract_pdfplumber_page_features
from app.classification.pymupdf_features import PyMuPDFPageFeatures, extract_pymupdf_page_features
from app.classification.rules import classify_page_result, is_definitely_complex_from_pymupdf
from app.classification.types import PageClassificationResult, PageSignals, PdfClassificationOutput
from app.config.settings import Settings


class PdfClassificationError(Exception):
    """Raised when PDF bytes cannot be classified."""


class PdfClassificationService:
    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings

    def classify_bytes(self, data: bytes) -> PdfClassificationOutput:
        pymupdf_features = extract_pymupdf_page_features(data)
        page_numbers = set(pymupdf_features)
        if not page_numbers:
            page_count = 0
        else:
            page_count = max(page_numbers)
        if page_count == 0:
            msg = "PDF has no pages"
            raise PdfClassificationError(msg)
        if page_count > self._settings.classification_max_pages:
            msg = (
                f"PDF page count {page_count} exceeds limit "
                f"{self._settings.classification_max_pages}"
            )
            raise PdfClassificationError(msg)

        page_text_by_number = {
            page_number: features.text for page_number, features in pymupdf_features.items()
        }
        borderline_page_numbers: list[int] = []
        for page_number in range(1, page_count + 1):
            pymupdf_page = pymupdf_features.get(page_number)
            signals = _pymupdf_only_signals(page_number, pymupdf_page)
            if not is_definitely_complex_from_pymupdf(signals):
                borderline_page_numbers.append(page_number)

        pdfplumber_features = (
            extract_pdfplumber_page_features(data, page_numbers=borderline_page_numbers)
            if borderline_page_numbers
            else {}
        )

        results: list[PageClassificationResult] = []
        for page_number in range(1, page_count + 1):
            pymupdf_page = pymupdf_features.get(page_number)
            pdfplumber_page = pdfplumber_features.get(page_number)
            signals = PageSignals(
                page_number=page_number,
                native_text_char_count=(pymupdf_page.native_text_char_count if pymupdf_page else 0),
                text_quality_score=pymupdf_page.text_quality_score if pymupdf_page else 0.0,
                image_area_ratio=pymupdf_page.image_area_ratio if pymupdf_page else 0.0,
                column_estimate=pymupdf_page.column_estimate if pymupdf_page else 1,
                table_score=pdfplumber_page.table_score if pdfplumber_page else 0.0,
                line_rect_density=pdfplumber_page.line_rect_density if pdfplumber_page else 0.0,
            )
            results.append(classify_page_result(signals))

        return PdfClassificationOutput(pages=results, page_text_by_number=page_text_by_number)


def _pymupdf_only_signals(
    page_number: int,
    pymupdf_page: PyMuPDFPageFeatures | None,
) -> PageSignals:
    if pymupdf_page is None:
        return PageSignals(
            page_number=page_number,
            native_text_char_count=0,
            text_quality_score=0.0,
            image_area_ratio=0.0,
            column_estimate=1,
            table_score=0.0,
            line_rect_density=0.0,
        )
    return PageSignals(
        page_number=page_number,
        native_text_char_count=pymupdf_page.native_text_char_count,
        text_quality_score=pymupdf_page.text_quality_score,
        image_area_ratio=pymupdf_page.image_area_ratio,
        column_estimate=pymupdf_page.column_estimate,
        table_score=0.0,
        line_rect_density=0.0,
    )
