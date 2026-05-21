from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageExtract:
    page_number: int
    content_text: str
    extractor: str
