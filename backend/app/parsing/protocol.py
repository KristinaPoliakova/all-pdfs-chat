from __future__ import annotations

from typing import Protocol

from app.classification.types import PageClass, PageClassificationResult
from app.parsing.types import PageExtract


class DocumentParser(Protocol):
    async def parse_document(
        self,
        pdf_bytes: bytes,
        pages: list[PageClassificationResult],
    ) -> list[PageExtract]: ...


class AzureComplexPageParser(Protocol):
    async def parse_pages(
        self,
        pdf_bytes: bytes,
        *,
        page_numbers: list[int],
    ) -> list[PageExtract]: ...


def split_pages_by_class(
    pages: list[PageClassificationResult],
) -> tuple[list[int], list[int]]:
    simple_pages: list[int] = []
    complex_pages: list[int] = []
    for page in pages:
        if page.page_class == PageClass.BORN_DIGITAL_SIMPLE:
            simple_pages.append(page.page_number)
        else:
            complex_pages.append(page.page_number)
    return simple_pages, complex_pages
