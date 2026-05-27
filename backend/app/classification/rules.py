from __future__ import annotations

from app.classification.thresholds import DEFAULT_THRESHOLDS, ClassifierThresholds
from app.classification.types import PageClass, PageClassificationResult, PageSignals


def classify_page(
    signals: PageSignals,
    *,
    thresholds: ClassifierThresholds = DEFAULT_THRESHOLDS,
) -> tuple[PageClass, float]:
    if _is_image_dominant_low_text(signals, thresholds):
        return PageClass.BORN_DIGITAL_COMPLEX, _complex_confidence(signals, thresholds)

    if _has_unreliable_text(signals, thresholds):
        return PageClass.BORN_DIGITAL_COMPLEX, _complex_confidence(signals, thresholds)

    if _has_layout_complexity(signals, thresholds):
        return PageClass.BORN_DIGITAL_COMPLEX, _complex_confidence(signals, thresholds)

    if _is_confidently_simple(signals, thresholds):
        return PageClass.BORN_DIGITAL_SIMPLE, _simple_confidence(signals, thresholds)

    return PageClass.BORN_DIGITAL_COMPLEX, _complex_confidence(signals, thresholds)


def classify_page_result(
    signals: PageSignals,
    *,
    thresholds: ClassifierThresholds = DEFAULT_THRESHOLDS,
) -> PageClassificationResult:
    page_class, confidence = classify_page(signals, thresholds=thresholds)
    return PageClassificationResult(
        page_number=signals.page_number,
        page_class=page_class,
        confidence=confidence,
    )


def _is_image_dominant_low_text(signals: PageSignals, thresholds: ClassifierThresholds) -> bool:
    return (
        signals.image_area_ratio >= thresholds.image_dominant_ratio
        and signals.native_text_char_count <= thresholds.image_dominant_max_text_chars
    )


def _has_unreliable_text(signals: PageSignals, thresholds: ClassifierThresholds) -> bool:
    if signals.native_text_char_count < thresholds.min_native_text_chars:
        return True
    if signals.text_quality_score < thresholds.min_text_quality:
        return True
    return False


def _has_layout_complexity(signals: PageSignals, thresholds: ClassifierThresholds) -> bool:
    if signals.table_score >= thresholds.table_score_threshold:
        return True
    if signals.column_estimate >= 2:
        return True
    if signals.line_rect_density >= thresholds.line_rect_density_threshold:
        return True
    return False


def _is_confidently_simple(signals: PageSignals, thresholds: ClassifierThresholds) -> bool:
    if signals.text_quality_score < thresholds.high_text_quality:
        return False
    if signals.native_text_char_count < thresholds.min_native_text_chars:
        return False
    if signals.image_area_ratio > thresholds.max_image_area_ratio:
        return False
    if signals.table_score >= thresholds.table_score_threshold:
        return False
    if signals.column_estimate >= 2:
        return False
    if signals.line_rect_density >= thresholds.line_rect_density_threshold:
        return False
    return True


def _simple_confidence(signals: PageSignals, thresholds: ClassifierThresholds) -> float:
    return min(
        1.0,
        max(
            signals.text_quality_score,
            1.0 - signals.image_area_ratio,
            thresholds.simple_confidence_floor,
        ),
    )


def _complex_confidence(signals: PageSignals, thresholds: ClassifierThresholds) -> float:
    return min(signals.text_quality_score, thresholds.simple_confidence_floor - 0.01)


def is_definitely_complex_from_pymupdf(
    signals: PageSignals,
    *,
    thresholds: ClassifierThresholds = DEFAULT_THRESHOLDS,
) -> bool:
    """True when pdfplumber layout signals cannot change the page class to simple."""
    if _is_image_dominant_low_text(signals, thresholds):
        return True
    if _has_unreliable_text(signals, thresholds):
        return True
    return signals.column_estimate >= 2
