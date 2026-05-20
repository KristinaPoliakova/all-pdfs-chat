from __future__ import annotations

from app.classification.pymupdf_features import extract_pymupdf_page_features

from tests.pdf_fixtures import make_text_pdf_bytes


def test_extract_pymupdf_page_features_returns_one_based_page_numbers() -> None:
    data = make_text_pdf_bytes(pages=2)

    features = extract_pymupdf_page_features(data)

    assert sorted(features) == [1, 2]
    assert features[1].native_text_char_count > 50
    assert features[1].text_quality_score > 0.5
    assert features[1].image_area_ratio < 0.5
