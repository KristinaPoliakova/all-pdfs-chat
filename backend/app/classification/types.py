from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PageClass(StrEnum):
    BORN_DIGITAL_SIMPLE = "born_digital_simple"
    BORN_DIGITAL_COMPLEX = "born_digital_complex"


class PdfProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    CLASSIFYING = "classifying"
    CLASSIFIED = "classified"
    CLASSIFICATION_FAILED = "classification_failed"


@dataclass(frozen=True, slots=True)
class PageSignals:
    """Per-page features from PyMuPDF and pdfplumber."""

    page_number: int
    native_text_char_count: int
    text_quality_score: float
    image_area_ratio: float
    column_estimate: int
    table_score: float
    line_rect_density: float


@dataclass(frozen=True, slots=True)
class PageClassificationResult:
    page_number: int
    page_class: PageClass
    confidence: float
    signals_json: str | None = None
