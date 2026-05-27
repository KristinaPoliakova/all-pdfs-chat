from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.application.ports.jobs import JobStatus
from app.infrastructure.persistence.memory.jobs import InMemoryJobQueue


@pytest.mark.asyncio
async def test_enqueue_and_claim_returns_running_job() -> None:
    queue = InMemoryJobQueue()

    job = await queue.enqueue(pdf_document_id="pdf-1", job_type="process_pdf")
    assert job.status == JobStatus.PENDING

    claimed = await queue.claim_next(worker_id="worker-1")
    assert claimed is not None
    assert claimed.pdf_document_id == "pdf-1"
    assert claimed.status == JobStatus.RUNNING
    assert claimed.locked_by == "worker-1"


@pytest.mark.asyncio
async def test_enqueue_duplicate_pdf_document_id_is_idempotent() -> None:
    queue = InMemoryJobQueue()

    first = await queue.enqueue(pdf_document_id="pdf-1", job_type="process_pdf")
    second = await queue.enqueue(pdf_document_id="pdf-1", job_type="process_pdf")

    assert second.id == first.id


@pytest.mark.asyncio
async def test_fail_or_retry_requeues_until_max_attempts() -> None:
    queue = InMemoryJobQueue(max_attempts=2)
    await queue.enqueue(pdf_document_id="pdf-1", job_type="process_pdf")
    claimed = await queue.claim_next(worker_id="worker-1")
    assert claimed is not None

    await queue.fail_or_retry(claimed.id, error="boom")
    retried = await queue.get_by_pdf_document_id("pdf-1")
    assert retried.status == JobStatus.PENDING
    assert retried.attempts == 1

    claimed_again = await queue.claim_next(worker_id="worker-1")
    assert claimed_again is not None
    await queue.fail_or_retry(claimed_again.id, error="boom again")
    failed = await queue.get_by_pdf_document_id("pdf-1")
    assert failed.status == JobStatus.FAILED
    assert failed.attempts == 2


@pytest.mark.asyncio
async def test_release_stale_locks_returns_job_to_pending() -> None:
    queue = InMemoryJobQueue()
    job = await queue.enqueue(pdf_document_id="pdf-1", job_type="process_pdf")
    claimed = await queue.claim_next(worker_id="worker-1")
    assert claimed is not None

    released = await queue.release_stale_locks(
        older_than=datetime.now(UTC) + timedelta(seconds=1),
    )
    assert released == 1

    updated = await queue.get_by_pdf_document_id("pdf-1")
    assert updated.status == JobStatus.PENDING
    assert updated.id == job.id
