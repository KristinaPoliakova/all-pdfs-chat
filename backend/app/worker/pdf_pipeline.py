from __future__ import annotations

import asyncio
import logging
import time

from app.classification.service import PdfClassificationService
from app.classification.types import PageClassificationResult, PdfProcessingStatus
from app.config.settings import Settings
from app.parsing.protocol import DocumentParser
from app.pdf_repository.protocol import PdfRecord, PdfRepository
from app.storage.protocol import FileStorage

logger = logging.getLogger(__name__)

_MAX_ERROR_LENGTH = 500


class PdfProcessingPipeline:
    def __init__(
        self,
        *,
        pdf_repository: PdfRepository,
        storage: FileStorage,
        settings: Settings,
        classifier: PdfClassificationService,
        parser: DocumentParser,
    ) -> None:
        self._pdf_repository = pdf_repository
        self._storage = storage
        self._settings = settings
        self._classifier = classifier
        self._parser = parser

    async def run(self, pdf_id: str) -> None:
        started = time.monotonic()
        record = await self._pdf_repository.get(pdf_id)
        data = await asyncio.to_thread(self._storage.download, record.storage_key)
        extract_count = 0

        if self._settings.classification_enabled:
            await self._phase_classify(pdf_id, data)
            record = await self._pdf_repository.get(pdf_id)
            if record.processing_status == PdfProcessingStatus.CLASSIFICATION_FAILED:
                _log_processed(pdf_id, record.filename, record, extract_count, started)
                return

        extract_count = await self._phase_parse(pdf_id, data)
        record = await self._pdf_repository.get(pdf_id)
        _log_processed(pdf_id, record.filename, record, extract_count, started)

    async def _phase_classify(self, pdf_id: str, data: bytes) -> list[PageClassificationResult]:
        from datetime import UTC, datetime

        await self._pdf_repository.set_processing_status(
            pdf_id,
            PdfProcessingStatus.CLASSIFYING,
        )
        try:
            pages = await asyncio.to_thread(self._classifier.classify_bytes, data)
        except Exception as exc:
            error = str(exc)[:_MAX_ERROR_LENGTH]
            await self._pdf_repository.set_processing_status(
                pdf_id,
                PdfProcessingStatus.CLASSIFICATION_FAILED,
                error=error,
            )
            logger.warning("PDF classify failed id=%s: %s", pdf_id, error)
            return []

        classified_at = datetime.now(UTC)
        await self._pdf_repository.save_page_classifications(
            pdf_id,
            pages,
            page_count=len(pages),
            classified_at=classified_at,
        )
        await self._pdf_repository.set_processing_status(
            pdf_id,
            PdfProcessingStatus.CLASSIFIED,
        )
        return pages

    async def _phase_parse(self, pdf_id: str, data: bytes) -> int:
        pages = await self._pdf_repository.get_pages(pdf_id)
        if not pages:
            await self._pdf_repository.set_processing_status(pdf_id, PdfProcessingStatus.PARSED)
            return 0

        await self._pdf_repository.set_processing_status(pdf_id, PdfProcessingStatus.PARSING)
        try:
            extracts = await self._parser.parse_document(data, pages)
            if extracts:
                await self._pdf_repository.save_page_extracts(pdf_id, extracts)
            await self._pdf_repository.set_processing_status(pdf_id, PdfProcessingStatus.PARSED)
            return len(extracts)
        except Exception as exc:
            error = str(exc)[:_MAX_ERROR_LENGTH]
            await self._pdf_repository.set_processing_status(
                pdf_id,
                PdfProcessingStatus.PARSING_FAILED,
                error=error,
            )
            logger.warning("PDF parse failed id=%s: %s", pdf_id, error)
            return 0


def _log_processed(
    pdf_id: str,
    filename: str,
    record: PdfRecord,
    extract_count: int,
    started: float,
) -> None:
    logger.info(
        "PDF processed id=%s file=%s status=%s pages=%s extracts=%d elapsed_ms=%d",
        pdf_id,
        filename,
        record.processing_status.value,
        record.page_count,
        extract_count,
        _elapsed_ms(started),
    )


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
