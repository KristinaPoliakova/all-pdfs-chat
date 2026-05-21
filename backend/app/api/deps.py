from __future__ import annotations

from fastapi import Depends

from app.config.settings import Settings, get_settings
from app.jobs.factory import create_job_queue
from app.jobs.protocol import JobQueue
from app.metadata.factory import create_pdf_metadata_store
from app.metadata.protocol import PdfMetadataStore
from app.services.pdf_upload import PdfUploadService
from app.storage.factory import create_file_storage
from app.storage.protocol import FileStorage


def get_file_storage() -> FileStorage:
    return create_file_storage()


def get_pdf_metadata_store() -> PdfMetadataStore:
    return create_pdf_metadata_store()


def get_job_queue() -> JobQueue:
    return create_job_queue()


def get_pdf_upload_service(
    metadata_store: PdfMetadataStore = Depends(get_pdf_metadata_store),
    storage: FileStorage = Depends(get_file_storage),
    settings: Settings = Depends(get_settings),
    job_queue: JobQueue = Depends(get_job_queue),
) -> PdfUploadService:
    return PdfUploadService(
        metadata_store=metadata_store,
        storage=storage,
        settings=settings,
        job_queue=job_queue,
    )
