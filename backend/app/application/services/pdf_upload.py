from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError

from app.application.ports.jobs import JobQueue
from app.application.ports.pdf import PdfRecord, PdfRepository
from app.application.ports.storage import FileStorage
from app.config.settings import MAX_FILENAME_LENGTH, Settings

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF"
_MIN_PDF_BYTES = 64
_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class PdfUploadResult:
    record: PdfRecord


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
        pdf_repository: PdfRepository,
        storage: FileStorage,
        settings: Settings,
        job_queue: JobQueue,
    ) -> None:
        self._pdf_repository = pdf_repository
        self._storage = storage
        self._settings = settings
        self._job_queue = job_queue

    async def upload(self, file: UploadFile, *, user_id: str) -> PdfUploadResult:
        filename, data = await read_pdf_upload(
            file,
            max_size_bytes=self._settings.max_upload_size_bytes,
        )
        storage_key = build_storage_key(filename)
        await asyncio.to_thread(self._storage.upload, storage_key, data)
        try:
            record = await self._pdf_repository.create(
                user_id=user_id,
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

        if self._settings.classification_enabled:
            await self._job_queue.enqueue(pdf_id=record.id, job_type="process_pdf")

        logger.info(
            "PDF uploaded id=%s filename=%s size_bytes=%d status=%s",
            record.id,
            record.filename,
            record.size_bytes,
            record.processing_status.value,
        )
        return PdfUploadResult(record=record)

    async def _remove_stored_file(self, storage_key: str) -> None:
        exists = await asyncio.to_thread(self._storage.exists, storage_key)
        if exists:
            await asyncio.to_thread(self._storage.delete, storage_key)
