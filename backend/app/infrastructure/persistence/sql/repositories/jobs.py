from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.jobs import JobStatus, PdfJobRecord
from app.infrastructure.persistence.sql.models.pdf_job import PdfJob


class SqlJobQueue:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        max_attempts: int = 3,
    ) -> None:
        self._session_factory = session_factory
        self._max_attempts = max_attempts

    async def enqueue(self, *, pdf_document_id: str, job_type: str) -> PdfJobRecord:
        async with self._session_factory() as session:
            existing = await session.execute(
                select(PdfJob).where(PdfJob.pdf_document_id == pdf_document_id),
            )
            row = existing.scalar_one_or_none()
            if row is not None:
                return _to_record(row)
            now = datetime.now(UTC)
            job = PdfJob(
                pdf_document_id=pdf_document_id,
                job_type=job_type,
                status=JobStatus.PENDING.value,
                attempts=0,
                max_attempts=self._max_attempts,
                run_after=now,
                updated_at=now,
            )
            session.add(job)
            try:
                await session.commit()
                await session.refresh(job)
            except Exception:
                await session.rollback()
                raise
        return _to_record(job)

    async def claim_next(self, *, worker_id: str) -> PdfJobRecord | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(PdfJob)
                    .where(PdfJob.status == JobStatus.PENDING.value)
                    .where(PdfJob.run_after <= now)
                    .order_by(PdfJob.created_at)
                    .limit(1)
                    .with_for_update(skip_locked=True),
                )
                job = result.scalar_one_or_none()
                if job is None:
                    return None
                job.status = JobStatus.RUNNING.value
                job.locked_at = now
                job.locked_by = worker_id
                job.updated_at = now
            await session.refresh(job)
        return _to_record(job)

    async def complete(self, job_id: str) -> None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            job = await session.get(PdfJob, job_id)
            if job is None:
                raise LookupError(f"Job not found: {job_id}")
            job.status = JobStatus.COMPLETED.value
            job.locked_at = None
            job.locked_by = None
            job.last_error = None
            job.updated_at = now
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def fail_or_retry(self, job_id: str, *, error: str) -> None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            job = await session.get(PdfJob, job_id)
            if job is None:
                raise LookupError(f"Job not found: {job_id}")
            attempts = job.attempts + 1
            job.attempts = attempts
            job.last_error = error
            job.locked_at = None
            job.locked_by = None
            job.updated_at = now
            if attempts >= job.max_attempts:
                job.status = JobStatus.FAILED.value
            else:
                backoff_seconds = min(60, max(0, 2**attempts - 2))
                job.status = JobStatus.PENDING.value
                job.run_after = now + timedelta(seconds=backoff_seconds)
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def release_stale_locks(self, *, older_than: datetime) -> int:
        now = datetime.now(UTC)
        released = 0
        async with self._session_factory() as session:
            result = await session.execute(
                select(PdfJob).where(PdfJob.status == JobStatus.RUNNING.value),
            )
            jobs = result.scalars().all()
            older_than_utc = _as_utc(older_than)
            assert older_than_utc is not None
            for job in jobs:
                locked_at = _as_utc(job.locked_at)
                if locked_at is None or locked_at >= older_than_utc:
                    continue
                job.status = JobStatus.PENDING.value
                job.locked_at = None
                job.locked_by = None
                job.updated_at = now
                released += 1
            if released:
                try:
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
        return released

    async def get_by_pdf_document_id(self, pdf_document_id: str) -> PdfJobRecord:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PdfJob).where(PdfJob.pdf_document_id == pdf_document_id),
            )
            job = result.scalar_one_or_none()
            if job is None:
                raise LookupError(f"Job not found for pdf_document_id: {pdf_document_id}")
        return _to_record(job)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _to_record(job: PdfJob) -> PdfJobRecord:
    return PdfJobRecord(
        id=job.id,
        pdf_document_id=job.pdf_document_id,
        job_type=job.job_type,
        status=JobStatus(job.status),
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        run_after=job.run_after,
        locked_at=job.locked_at,
        locked_by=job.locked_by,
        last_error=job.last_error,
    )
