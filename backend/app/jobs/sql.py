from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.sqlite_paths import sqlite_file_path
from app.jobs.protocol import JobStatus, PdfJobRecord
from app.models.pdf_job import PdfJob


class SqlJobQueue:
    def __init__(self, database_url: str, *, max_attempts: int = 3) -> None:
        self._database_url = database_url
        self._max_attempts = max_attempts
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def init(self) -> None:
        _ensure_sqlite_parent_dir(self._database_url)
        engine = self._get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._session_factory = None

    async def enqueue(self, *, pdf_id: str, job_type: str) -> PdfJobRecord:
        factory = self._get_session_factory()
        async with factory() as session:
            existing = await session.execute(
                select(PdfJob).where(PdfJob.pdf_id == pdf_id),
            )
            row = existing.scalar_one_or_none()
            if row is not None:
                return _to_record(row)
            now = datetime.now(UTC)
            job = PdfJob(
                pdf_id=pdf_id,
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
        factory = self._get_session_factory()
        now = datetime.now(UTC)
        async with factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(PdfJob)
                    .where(PdfJob.status == JobStatus.PENDING.value)
                    .where(PdfJob.run_after <= now)
                    .order_by(PdfJob.created_at)
                    .limit(1),
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
        factory = self._get_session_factory()
        now = datetime.now(UTC)
        async with factory() as session:
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
        factory = self._get_session_factory()
        now = datetime.now(UTC)
        async with factory() as session:
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
        factory = self._get_session_factory()
        now = datetime.now(UTC)
        released = 0
        async with factory() as session:
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

    async def get_by_pdf_id(self, pdf_id: str) -> PdfJobRecord:
        factory = self._get_session_factory()
        async with factory() as session:
            result = await session.execute(select(PdfJob).where(PdfJob.pdf_id == pdf_id))
            job = result.scalar_one_or_none()
            if job is None:
                raise LookupError(f"Job not found for pdf_id: {pdf_id}")
        return _to_record(job)

    def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                self._database_url,
                echo=False,
                pool_pre_ping=True,
            )
        return self._engine

    def _get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self._get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    db_path = sqlite_file_path(database_url)
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _to_record(job: PdfJob) -> PdfJobRecord:
    return PdfJobRecord(
        id=job.id,
        pdf_id=job.pdf_id,
        job_type=job.job_type,
        status=JobStatus(job.status),
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        run_after=job.run_after,
        locked_at=job.locked_at,
        locked_by=job.locked_by,
        last_error=job.last_error,
    )
