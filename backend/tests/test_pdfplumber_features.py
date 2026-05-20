from __future__ import annotations

from app.classification.pdfplumber_features import extract_pdfplumber_page_features

from tests.pdf_fixtures import make_text_pdf_bytes


def test_extract_pdfplumber_page_features_returns_one_based_page_numbers() -> None:
    data = make_text_pdf_bytes(pages=1)

    features = extract_pdfplumber_page_features(data)

    assert 1 in features
    assert features[1].table_score >= 0.0
    assert features[1].line_rect_density >= 0.0
