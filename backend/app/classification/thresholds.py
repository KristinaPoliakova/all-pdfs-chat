from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassifierThresholds:
    """Deterministic thresholds for page routing (PyMuPDF + pdfplumber only)."""

    min_native_text_chars: int = 50
    min_text_quality: float = 0.6
    high_text_quality: float = 0.8
    table_score_threshold: float = 0.3
    line_rect_density_threshold: float = 0.25
    max_image_area_ratio: float = 0.35
    image_dominant_ratio: float = 0.65
    image_dominant_max_text_chars: int = 20
    simple_confidence_floor: float = 0.85


DEFAULT_THRESHOLDS = ClassifierThresholds()
