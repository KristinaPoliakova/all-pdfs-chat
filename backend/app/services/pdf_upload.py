from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError

from app.classification.service import PdfClassificationService
from app.classification.types import PageClassificationResult, PdfProcessingStatus
from app.config.settings import MAX_FILENAME_LENGTH, Settings
from app.metadata.protocol import PdfMetadataRecord, PdfMetadataStore
from app.storage.protocol import FileStorage

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF"
_MIN_PDF_BYTES = 64
_CHUNK_SIZE = 1024 * 1024
_MAX_CLASSIFICATION_ERROR_LENGTH = 500


@dataclass(frozen=True, slots=True)
class PdfUploadResult:
    record: PdfMetadataRecord
    pages: list[PageClassificationResult]


async def read_pdf_upload(file: UploadFile, *, max_size_bytes: int) -> tuple[str, bytes]:
    if file.filename is None or not file.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    filename = Path(file.filename).name
    if len(filename) > MAX_FILENAME_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Filename must be at most {MAX_FILENAME_LENGTH} characters",
        )

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    if file.size is not None and file.size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_size_bytes} bytes",
        )

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum size of {max_size_bytes} bytes",
            )
        chunks.append(chunk)

    data = b"".join(chunks)
    if len(data) < _MIN_PDF_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF file is too small to be valid",
        )

    if not data.startswith(_PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    return filename, data


def build_storage_key(filename: str) -> str:
    safe_name = PurePosixPath(Path(filename).name).name
    return f"pdfs/{uuid.uuid4()}-{safe_name}"


class PdfUploadService:
    def __init__(
        self,
        *,
        metadata_store: PdfMetadataStore,
        storage: FileStorage,
        settings: Settings,
        classifier: PdfClassificationService | None = None,
    ) -> None:
        self._metadata_store = metadata_store
        self._storage = storage
        self._settings = settings
        self._classifier = classifier or PdfClassificationService(settings=settings)

    async def upload(self, file: UploadFile) -> PdfUploadResult:
        filename, data = await read_pdf_upload(
            file,
            max_size_bytes=self._settings.max_upload_size_bytes,
        )
        storage_key = build_storage_key(filename)
        await asyncio.to_thread(self._storage.upload, storage_key, data)
        try:
            record = await self._metadata_store.create(
                filename=filename,
                storage_key=storage_key,
                size_bytes=len(data),
            )
        except IntegrityError:
            await self._remove_stored_file(storage_key)
            raise
        except Exception:
            await self._remove_stored_file(storage_key)
            raise

        pages: list[PageClassificationResult] = []
        if self._settings.classification_enabled:
            pages = await self._classify_and_persist(record.id, data)
            record = await self._metadata_store.get(record.id)

        logger.info(
            "PDF uploaded id=%s filename=%s size_bytes=%d status=%s pages=%d",
            record.id,
            record.filename,
            record.size_bytes,
            record.processing_status.value,
            len(pages),
        )
        return PdfUploadResult(record=record, pages=pages)

    async def _classify_and_persist(
        self,
        pdf_id: str,
        data: bytes,
    ) -> list[PageClassificationResult]:
        try:
            pages = await asyncio.to_thread(self._classifier.classify_bytes, data)
        except Exception as exc:
            error = str(exc)[:_MAX_CLASSIFICATION_ERROR_LENGTH]
            await self._metadata_store.set_processing_status(
                pdf_id,
                PdfProcessingStatus.CLASSIFICATION_FAILED,
                error=error,
            )
            logger.warning("PDF classification failed id=%s error=%s", pdf_id, error)
            return []

        classified_at = datetime.now(UTC)
        await self._metadata_store.save_page_classifications(
            pdf_id,
            pages,
            page_count=len(pages),
            classified_at=classified_at,
        )
        await self._metadata_store.set_processing_status(
            pdf_id,
            PdfProcessingStatus.CLASSIFIED,
        )
        return pages

    async def _remove_stored_file(self, storage_key: str) -> None:
        exists = await asyncio.to_thread(self._storage.exists, storage_key)
        if exists:
            await asyncio.to_thread(self._storage.delete, storage_key)
