from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PdfJobRecord:
    id: str
    pdf_document_id: str
    job_type: str
    status: JobStatus
    attempts: int
    max_attempts: int
    run_after: datetime
    locked_at: datetime | None
    locked_by: str | None
    last_error: str | None


class JobQueue(Protocol):
    async def enqueue(self, *, pdf_document_id: str, job_type: str) -> PdfJobRecord: ...

    async def claim_next(self, *, worker_id: str) -> PdfJobRecord | None: ...

    async def complete(self, job_id: str) -> None: ...

    async def fail_or_retry(self, job_id: str, *, error: str) -> None: ...

    async def release_stale_locks(self, *, older_than: datetime) -> int: ...

    async def get_by_pdf_document_id(self, pdf_document_id: str) -> PdfJobRecord: ...
