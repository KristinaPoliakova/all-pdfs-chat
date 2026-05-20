from __future__ import annotations

import pytest
from app.classification.rules import classify_page
from app.classification.thresholds import ClassifierThresholds
from app.classification.types import PageClass, PageSignals

_DEFAULT_THRESHOLDS = ClassifierThresholds()


def _signals(**overrides: object) -> PageSignals:
    defaults: dict[str, object] = {
        "page_number": 1,
        "native_text_char_count": 200,
        "text_quality_score": 0.9,
        "image_area_ratio": 0.05,
        "column_estimate": 1,
        "table_score": 0.0,
        "line_rect_density": 0.0,
    }
    defaults.update(overrides)
    return PageSignals(**defaults)  # type: ignore[arg-type]


def test_image_dominant_low_text_routes_to_born_digital_complex() -> None:
    page_class, _ = classify_page(
        _signals(native_text_char_count=5, image_area_ratio=0.8, text_quality_score=0.1),
        thresholds=_DEFAULT_THRESHOLDS,
    )

    assert page_class == PageClass.BORN_DIGITAL_COMPLEX


@pytest.mark.parametrize(
    "overrides",
    [
        {"native_text_char_count": 10},
        {"text_quality_score": 0.2},
    ],
)
def test_unreliable_text_routes_to_born_digital_complex(overrides: dict[str, object]) -> None:
    page_class, _ = classify_page(_signals(**overrides), thresholds=_DEFAULT_THRESHOLDS)

    assert page_class == PageClass.BORN_DIGITAL_COMPLEX


@pytest.mark.parametrize(
    "overrides",
    [
        {"table_score": 0.5},
        {"column_estimate": 2},
        {"line_rect_density": 0.4},
    ],
)
def test_layout_complexity_routes_to_born_digital_complex(overrides: dict[str, object]) -> None:
    page_class, _ = classify_page(_signals(**overrides), thresholds=_DEFAULT_THRESHOLDS)

    assert page_class == PageClass.BORN_DIGITAL_COMPLEX


def test_clean_page_is_born_digital_simple() -> None:
    page_class, confidence = classify_page(_signals(), thresholds=_DEFAULT_THRESHOLDS)

    assert page_class == PageClass.BORN_DIGITAL_SIMPLE
    assert confidence >= _DEFAULT_THRESHOLDS.simple_confidence_floor


def test_borderline_text_quality_defaults_to_born_digital_complex() -> None:
    page_class, _ = classify_page(
        _signals(text_quality_score=0.75),
        thresholds=_DEFAULT_THRESHOLDS,
    )

    assert page_class == PageClass.BORN_DIGITAL_COMPLEX


def test_high_image_area_prevents_born_digital_simple() -> None:
    page_class, _ = classify_page(
        _signals(image_area_ratio=0.6),
        thresholds=_DEFAULT_THRESHOLDS,
    )

    assert page_class == PageClass.BORN_DIGITAL_COMPLEX


def test_moderate_text_with_low_image_can_be_simple() -> None:
    page_class, _ = classify_page(
        _signals(
            native_text_char_count=120,
            text_quality_score=0.85,
            image_area_ratio=0.1,
        ),
        thresholds=_DEFAULT_THRESHOLDS,
    )

    assert page_class == PageClass.BORN_DIGITAL_SIMPLE
