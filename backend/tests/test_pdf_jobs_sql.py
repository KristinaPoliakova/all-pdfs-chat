from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.jobs.protocol import JobStatus
from app.jobs.sql import SqlJobQueue


@pytest.mark.asyncio
async def test_sql_enqueue_claim_and_complete() -> None:
    queue = SqlJobQueue("sqlite+aiosqlite:///:memory:", max_attempts=3)
    await queue.init()

    await queue.enqueue(pdf_id="pdf-1", job_type="process_pdf")
    claimed = await queue.claim_next(worker_id="worker-a")
    assert claimed is not None
    assert claimed.pdf_id == "pdf-1"
    assert claimed.status == JobStatus.RUNNING

    await queue.complete(claimed.id)
    done = await queue.get_by_pdf_id("pdf-1")
    assert done.status == JobStatus.COMPLETED

    await queue.close()


@pytest.mark.asyncio
async def test_sql_enqueue_is_idempotent_per_pdf_id() -> None:
    queue = SqlJobQueue("sqlite+aiosqlite:///:memory:")
    await queue.init()

    first = await queue.enqueue(pdf_id="pdf-1", job_type="process_pdf")
    second = await queue.enqueue(pdf_id="pdf-1", job_type="process_pdf")
    assert second.id == first.id

    await queue.close()


@pytest.mark.asyncio
async def test_sql_release_stale_locks() -> None:
    queue = SqlJobQueue("sqlite+aiosqlite:///:memory:")
    await queue.init()
    await queue.enqueue(pdf_id="pdf-1", job_type="process_pdf")
    claimed = await queue.claim_next(worker_id="worker-a")
    assert claimed is not None

    released = await queue.release_stale_locks(
        older_than=datetime.now(UTC) + timedelta(seconds=1),
    )
    assert released == 1

    updated = await queue.get_by_pdf_id("pdf-1")
    assert updated.status == JobStatus.PENDING

    await queue.close()
