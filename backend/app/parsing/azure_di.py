from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

from app.config.settings import Settings
from app.parsing.types import PageExtract

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential

EXTRACTOR_NAME = "azure_document_intelligence"
MODEL_ID = "prebuilt-read"


def format_azure_pages_parameter(page_numbers: list[int]) -> str:
    """Format 1-based page numbers for Azure DI's pages query parameter (e.g. '1-3,5,7')."""
    if not page_numbers:
        msg = "page_numbers must not be empty"
        raise ValueError(msg)
    sorted_pages = sorted(set(page_numbers))
    ranges: list[str] = []
    range_start = sorted_pages[0]
    range_end = range_start
    for page in sorted_pages[1:]:
        if page == range_end + 1:
            range_end = page
            continue
        ranges.append(_format_page_range(range_start, range_end))
        range_start = range_end = page
    ranges.append(_format_page_range(range_start, range_end))
    return ",".join(ranges)


def _format_page_range(start: int, end: int) -> str:
    if start == end:
        return str(start)
    return f"{start}-{end}"


class AzureDocumentIntelligenceParser:
    def __init__(
        self,
        *,
        settings: Settings,
        client: DocumentIntelligenceClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client

    async def parse_pages(
        self,
        pdf_bytes: bytes,
        *,
        page_numbers: list[int],
    ) -> list[PageExtract]:
        if not page_numbers:
            return []
        return await asyncio.to_thread(
            self._analyze_and_map,
            pdf_bytes,
            page_numbers,
        )

    def _analyze_and_map(self, pdf_bytes: bytes, page_numbers: list[int]) -> list[PageExtract]:
        client = self._get_client()
        pages_param = format_azure_pages_parameter(page_numbers)
        poller = client.begin_analyze_document(
            MODEL_ID,
            AnalyzeDocumentRequest(bytes_source=pdf_bytes),
            pages=pages_param,
        )
        deadline = time.monotonic() + self._settings.parsing_max_wait_seconds
        while not poller.done():
            if time.monotonic() >= deadline:
                msg = (
                    f"Azure Document Intelligence timed out after "
                    f"{self._settings.parsing_max_wait_seconds}s"
                )
                raise TimeoutError(msg)
            time.sleep(self._settings.parsing_poll_interval_seconds)

        result = poller.result()
        requested = set(page_numbers)
        extracts: list[PageExtract] = []
        for page in result.pages or []:
            if page.page_number not in requested:
                continue
            lines = [line.content for line in page.lines or [] if line.content]
            content_text = "\n".join(lines)
            extracts.append(
                PageExtract(
                    page_number=page.page_number,
                    content_text=content_text,
                    extractor=EXTRACTOR_NAME,
                ),
            )
        extracts.sort(key=lambda extract: extract.page_number)
        return extracts

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def _get_client(self) -> DocumentIntelligenceClient:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self) -> DocumentIntelligenceClient:
        endpoint = self._settings.azure_document_intelligence_endpoint.strip()
        if not endpoint:
            msg = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT is required when parsing is enabled"
            raise ValueError(msg)
        credential = self._build_credential()
        return DocumentIntelligenceClient(endpoint=endpoint, credential=credential)

    def _build_credential(self) -> AzureKeyCredential | TokenCredential:
        api_key = self._settings.azure_document_intelligence_api_key.strip()
        if api_key:
            return AzureKeyCredential(api_key)
        if self._settings.is_prod:
            from azure.identity import DefaultAzureCredential

            return DefaultAzureCredential()
        msg = "AZURE_DOCUMENT_INTELLIGENCE_API_KEY is required when PARSING_ENABLED in dev"
        raise ValueError(msg)
