from __future__ import annotations

from dataclasses import dataclass

import fitz  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class PyMuPDFPageFeatures:
    native_text_char_count: int
    text_quality_score: float
    image_area_ratio: float
    column_estimate: int
    text: str


def extract_pymupdf_page_features(data: bytes) -> dict[int, PyMuPDFPageFeatures]:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        features: dict[int, PyMuPDFPageFeatures] = {}
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            text = page.get_text()
            stripped_text = text.strip()
            features[page_index + 1] = PyMuPDFPageFeatures(
                native_text_char_count=len(stripped_text),
                text_quality_score=_text_quality_score(text),
                image_area_ratio=_image_area_ratio(page),
                column_estimate=_estimate_columns(page),
                text=stripped_text,
            )
        return features
    finally:
        doc.close()


def _text_quality_score(text: str) -> float:
    stripped = text.strip()
    if not stripped:
        return 0.0
    alnum = sum(1 for character in stripped if character.isalnum())
    alnum_ratio = alnum / len(stripped)
    word_factor = min(1.0, len(stripped.split()) / 25.0)
    return min(1.0, alnum_ratio * 0.6 + word_factor * 0.4)


def _image_area_ratio(page: fitz.Page) -> float:
    page_area = float(page.rect.width) * float(page.rect.height)
    if page_area <= 0:
        return 0.0
    image_area = 0.0
    for image in page.get_images(full=True):
        xref = image[0]
        for rect in page.get_image_rects(xref):
            image_area += float(rect.width) * float(rect.height)
    return min(1.0, image_area / page_area)


def _estimate_columns(page: fitz.Page) -> int:
    words = page.get_text("words")
    if len(words) < 8:
        return 1
    page_width = float(page.rect.width)
    if page_width <= 0:
        return 1
    x_positions = sorted({round((word[0] + word[2]) / 2, 0) for word in words})
    clusters = 1
    gap_threshold = page_width * 0.12
    for index in range(1, len(x_positions)):
        if x_positions[index] - x_positions[index - 1] >= gap_threshold:
            clusters += 1
    return max(1, min(clusters, 4))
