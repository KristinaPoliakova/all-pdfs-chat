from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.application.ports.jobs import JobStatus, PdfJobRecord


class InMemoryJobQueue:
    def __init__(self, *, max_attempts: int = 3) -> None:
        self._jobs: dict[str, PdfJobRecord] = {}
        self._pdf_id_to_job_id: dict[str, str] = {}
        self._max_attempts = max_attempts

    async def enqueue(self, *, pdf_id: str, job_type: str) -> PdfJobRecord:
        existing_id = self._pdf_id_to_job_id.get(pdf_id)
        if existing_id is not None:
            return self._jobs[existing_id]
        now = datetime.now(UTC)
        job = PdfJobRecord(
            id=str(uuid.uuid4()),
            pdf_id=pdf_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            attempts=0,
            max_attempts=self._max_attempts,
            run_after=now,
            locked_at=None,
            locked_by=None,
            last_error=None,
        )
        self._jobs[job.id] = job
        self._pdf_id_to_job_id[pdf_id] = job.id
        return job

    async def claim_next(self, *, worker_id: str) -> PdfJobRecord | None:
        now = datetime.now(UTC)
        pending = [
            job
            for job in self._jobs.values()
            if job.status == JobStatus.PENDING and job.run_after <= now
        ]
        if not pending:
            return None
        pending.sort(key=lambda job: job.run_after)
        job = pending[0]
        claimed = replace(
            job,
            status=JobStatus.RUNNING,
            locked_at=now,
            locked_by=worker_id,
        )
        self._jobs[job.id] = claimed
        return claimed

    async def complete(self, job_id: str) -> None:
        job = self._require_job(job_id)
        self._jobs[job_id] = replace(
            job,
            status=JobStatus.COMPLETED,
            locked_at=None,
            locked_by=None,
            last_error=None,
        )

    async def fail_or_retry(self, job_id: str, *, error: str) -> None:
        job = self._require_job(job_id)
        attempts = job.attempts + 1
        if attempts >= job.max_attempts:
            self._jobs[job_id] = replace(
                job,
                status=JobStatus.FAILED,
                attempts=attempts,
                locked_at=None,
                locked_by=None,
                last_error=error,
            )
            return
        backoff_seconds = min(60, max(0, 2**attempts - 2))
        self._jobs[job_id] = replace(
            job,
            status=JobStatus.PENDING,
            attempts=attempts,
            run_after=datetime.now(UTC) + timedelta(seconds=backoff_seconds),
            locked_at=None,
            locked_by=None,
            last_error=error,
        )

    async def release_stale_locks(self, *, older_than: datetime) -> int:
        released = 0
        for job_id, job in list(self._jobs.items()):
            if job.status != JobStatus.RUNNING or job.locked_at is None:
                continue
            if job.locked_at is not None and job.locked_at >= older_than:
                continue
            self._jobs[job_id] = replace(
                job,
                status=JobStatus.PENDING,
                locked_at=None,
                locked_by=None,
            )
            released += 1
        return released

    async def get_by_pdf_id(self, pdf_id: str) -> PdfJobRecord:
        job_id = self._pdf_id_to_job_id.get(pdf_id)
        if job_id is None:
            raise LookupError(f"Job not found for pdf_id: {pdf_id}")
        return self._jobs[job_id]

    def _require_job(self, job_id: str) -> PdfJobRecord:
        job = self._jobs.get(job_id)
        if job is None:
            raise LookupError(f"Job not found: {job_id}")
        return job
