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
        *,
        page_text_by_number: dict[int, str] | None = None,
    ) -> list[PageExtract]:
        simple_pages, complex_pages = split_pages_by_class(pages)
        results: list[PageExtract] = []
        cached_text = page_text_by_number or {}

        if simple_pages:
            cached_simple_pages = [page for page in simple_pages if page in cached_text]
            uncached_simple_pages = [page for page in simple_pages if page not in cached_text]

            for page_number in cached_simple_pages:
                results.append(
                    PageExtract(
                        page_number=page_number,
                        content_text=cached_text[page_number],
                        extractor="local_pymupdf",
                    ),
                )

            if uncached_simple_pages:
                simple_extracts = await asyncio.to_thread(
                    extract_page_text,
                    pdf_bytes,
                    uncached_simple_pages,
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

    def close(self) -> None:
        if self._azure_parser is not None:
            self._azure_parser.close()
