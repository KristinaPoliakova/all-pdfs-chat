from __future__ import annotations

from fastapi import Depends

from app.config.settings import Settings, get_settings
from app.jobs.factory import create_job_queue
from app.jobs.protocol import JobQueue
from app.pdf_repository.factory import create_pdf_repository
from app.pdf_repository.protocol import PdfRepository
from app.services.pdf_upload import PdfUploadService
from app.storage.factory import create_file_storage
from app.storage.protocol import FileStorage


def get_file_storage() -> FileStorage:
    return create_file_storage()


def get_pdf_repository() -> PdfRepository:
    return create_pdf_repository()


def get_job_queue() -> JobQueue:
    return create_job_queue()


def get_pdf_upload_service(
    pdf_repository: PdfRepository = Depends(get_pdf_repository),
    storage: FileStorage = Depends(get_file_storage),
    settings: Settings = Depends(get_settings),
    job_queue: JobQueue = Depends(get_job_queue),
) -> PdfUploadService:
    return PdfUploadService(
        pdf_repository=pdf_repository,
        storage=storage,
        settings=settings,
        job_queue=job_queue,
    )
