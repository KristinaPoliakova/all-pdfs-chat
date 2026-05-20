from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime

from app.classification.types import PageClassificationResult, PdfProcessingStatus
from app.metadata.protocol import PdfMetadataRecord


class InMemoryPdfMetadataStore:
    def __init__(self) -> None:
        self._records: dict[str, PdfMetadataRecord] = {}
        self._pages: dict[str, list[PageClassificationResult]] = {}

    async def init(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def create(
        self,
        *,
        filename: str,
        storage_key: str,
        size_bytes: int,
        processing_status: PdfProcessingStatus = PdfProcessingStatus.UPLOADED,
    ) -> PdfMetadataRecord:
        record = PdfMetadataRecord(
            id=str(uuid.uuid4()),
            filename=filename,
            storage_key=storage_key,
            size_bytes=size_bytes,
            created_at=datetime.now(UTC),
            processing_status=processing_status,
            page_count=None,
            classification_error=None,
            classified_at=None,
        )
        self._records[record.id] = record
        return record

    async def set_processing_status(
        self,
        pdf_id: str,
        status: PdfProcessingStatus,
        *,
        error: str | None = None,
    ) -> None:
        record = self._records.get(pdf_id)
        if record is None:
            raise LookupError(f"PDF document not found: {pdf_id}")
        self._records[pdf_id] = replace(
            record,
            processing_status=status,
            classification_error=error,
        )

    async def save_page_classifications(
        self,
        pdf_id: str,
        pages: list[PageClassificationResult],
        *,
        page_count: int,
        classified_at: datetime,
    ) -> None:
        record = self._records.get(pdf_id)
        if record is None:
            raise LookupError(f"PDF document not found: {pdf_id}")
        self._pages[pdf_id] = list(pages)
        self._records[pdf_id] = replace(
            record,
            page_count=page_count,
            classified_at=classified_at,
        )

    async def get(self, pdf_id: str) -> PdfMetadataRecord:
        record = self._records.get(pdf_id)
        if record is None:
            raise LookupError(f"PDF document not found: {pdf_id}")
        return record

    async def get_pages(self, pdf_id: str) -> list[PageClassificationResult]:
        return list(self._pages.get(pdf_id, []))
