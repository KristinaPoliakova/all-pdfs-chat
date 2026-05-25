from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.classification.types import PageClassificationResult, PdfProcessingStatus
from app.parsing.types import PageExtract


@dataclass(frozen=True, slots=True)
class PdfRecord:
    id: str
    filename: str
    storage_key: str
    size_bytes: int
    created_at: datetime
    processing_status: PdfProcessingStatus
    page_count: int | None
    classification_error: str | None
    classified_at: datetime | None
    parsing_error: str | None
    parsed_at: datetime | None


class PdfRepository(Protocol):
    async def create(
        self,
        *,
        filename: str,
        storage_key: str,
        size_bytes: int,
        processing_status: PdfProcessingStatus = PdfProcessingStatus.UPLOADED,
    ) -> PdfRecord: ...

    async def set_processing_status(
        self,
        pdf_id: str,
        status: PdfProcessingStatus,
        *,
        error: str | None = None,
    ) -> None: ...

    async def save_page_classifications(
        self,
        pdf_id: str,
        pages: list[PageClassificationResult],
        *,
        page_count: int,
        classified_at: datetime,
    ) -> None: ...

    async def get(self, pdf_id: str) -> PdfRecord: ...

    async def get_pages(self, pdf_id: str) -> list[PageClassificationResult]: ...

    async def save_page_extracts(
        self,
        pdf_id: str,
        extracts: list[PageExtract],
    ) -> None: ...

    async def get_page_extracts(self, pdf_id: str) -> list[PageExtract]: ...
