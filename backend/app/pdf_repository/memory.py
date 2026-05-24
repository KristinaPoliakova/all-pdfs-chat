from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime

from app.classification.types import PageClassificationResult, PdfProcessingStatus
from app.parsing.types import PageExtract
from app.pdf_repository.protocol import PdfRecord


class InMemoryPdfRepository:
    def __init__(self) -> None:
        self._records: dict[str, PdfRecord] = {}
        self._pages: dict[str, list[PageClassificationResult]] = {}
        self._extracts: dict[str, list[PageExtract]] = {}

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
    ) -> PdfRecord:
        record = PdfRecord(
            id=str(uuid.uuid4()),
            filename=filename,
            storage_key=storage_key,
            size_bytes=size_bytes,
            created_at=datetime.now(UTC),
            processing_status=processing_status,
            page_count=None,
            classification_error=None,
            classified_at=None,
            parsing_error=None,
            parsed_at=None,
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
        self._records[pdf_id] = _with_status(record, status, error=error)

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

    async def get(self, pdf_id: str) -> PdfRecord:
        record = self._records.get(pdf_id)
        if record is None:
            raise LookupError(f"PDF document not found: {pdf_id}")
        return record

    async def get_pages(self, pdf_id: str) -> list[PageClassificationResult]:
        return list(self._pages.get(pdf_id, []))

    async def save_page_extracts(
        self,
        pdf_id: str,
        extracts: list[PageExtract],
    ) -> None:
        if pdf_id not in self._records:
            raise LookupError(f"PDF document not found: {pdf_id}")
        self._extracts[pdf_id] = list(extracts)

    async def get_page_extracts(self, pdf_id: str) -> list[PageExtract]:
        return list(self._extracts.get(pdf_id, []))


def _with_status(
    record: PdfRecord,
    status: PdfProcessingStatus,
    *,
    error: str | None,
) -> PdfRecord:
    classification_error = record.classification_error
    parsing_error = record.parsing_error
    parsed_at = record.parsed_at

    if status in {
        PdfProcessingStatus.CLASSIFYING,
        PdfProcessingStatus.CLASSIFICATION_FAILED,
    }:
        classification_error = error
    elif status in {PdfProcessingStatus.PARSING, PdfProcessingStatus.PARSING_FAILED}:
        parsing_error = error
    elif status == PdfProcessingStatus.PARSED:
        parsed_at = datetime.now(UTC)
        parsing_error = None

    return replace(
        record,
        processing_status=status,
        classification_error=classification_error,
        parsing_error=parsing_error,
        parsed_at=parsed_at,
    )
