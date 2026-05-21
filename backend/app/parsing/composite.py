from __future__ import annotations

import asyncio

from app.classification.types import PageClassificationResult
from app.config.settings import Settings
from app.parsing.local_pymupdf import extract_page_text
from app.parsing.protocol import AzureComplexPageParser, split_pages_by_class
from app.parsing.types import PageExtract


class CompositeDocumentParser:
    def __init__(
        self,
        *,
        settings: Settings,
        azure_parser: AzureComplexPageParser | None = None,
    ) -> None:
        self._settings = settings
        self._azure_parser = azure_parser

    async def parse_document(
        self,
        pdf_bytes: bytes,
        pages: list[PageClassificationResult],
    ) -> list[PageExtract]:
        simple_pages, complex_pages = split_pages_by_class(pages)
        results: list[PageExtract] = []

        if simple_pages:
            simple_extracts = await asyncio.to_thread(
                extract_page_text,
                pdf_bytes,
                simple_pages,
            )
            results.extend(simple_extracts)

        if complex_pages and self._settings.parsing_enabled and self._azure_parser is not None:
            azure_extracts = await self._azure_parser.parse_pages(
                pdf_bytes,
                page_numbers=complex_pages,
            )
            results.extend(azure_extracts)

        results.sort(key=lambda extract: extract.page_number)
        return results
