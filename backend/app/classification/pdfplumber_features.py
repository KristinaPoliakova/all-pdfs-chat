from __future__ import annotations

import io
from dataclasses import dataclass

import pdfplumber


@dataclass(frozen=True, slots=True)
class PdfPlumberPageFeatures:
    table_score: float
    line_rect_density: float


def extract_pdfplumber_page_features(data: bytes) -> dict[int, PdfPlumberPageFeatures]:
    features: dict[int, PdfPlumberPageFeatures] = {}
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            features[page_index + 1] = PdfPlumberPageFeatures(
                table_score=_table_score(page),
                line_rect_density=_line_rect_density(page),
            )
    return features


def _table_score(page: pdfplumber.page.Page) -> float:
    tables = page.find_tables()
    if not tables:
        return 0.0
    page_area = page.width * page.height
    if page_area <= 0:
        return 1.0
    table_area = sum(
        (table.bbox[2] - table.bbox[0]) * (table.bbox[3] - table.bbox[1]) for table in tables
    )
    return min(1.0, table_area / page_area)


def _line_rect_density(page: pdfplumber.page.Page) -> float:
    line_count = len(page.lines or []) + len(page.rects or [])
    return min(1.0, line_count / 50.0)
