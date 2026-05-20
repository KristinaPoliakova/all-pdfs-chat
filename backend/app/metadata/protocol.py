from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.classification.types import PageClassificationResult, PdfProcessingStatus


@dataclass(frozen=True, slots=True)
class PdfMetadataRecord:
    id: str
    filename: str
    storage_key: str
    size_bytes: int
    created_at: datetime
    processing_status: PdfProcessingStatus
    page_count: int | None
    classification_error: str | None
    classified_at: datetime | None


class PdfMetadataStore(Protocol):
    async def init(self) -> None:
        """Create schema / prepare storage (no-op for in-memory)."""
        ...

    async def close(self) -> None:
        """Release connections (no-op for in-memory)."""
        ...

    async def create(
        self,
        *,
        filename: str,
        storage_key: str,
        size_bytes: int,
        processing_status: PdfProcessingStatus = PdfProcessingStatus.UPLOADED,
    ) -> PdfMetadataRecord: ...

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

    async def get(self, pdf_id: str) -> PdfMetadataRecord: ...

    async def get_pages(self, pdf_id: str) -> list[PageClassificationResult]: ...
