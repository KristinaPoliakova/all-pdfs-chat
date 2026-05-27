from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from app.application.ports.jobs import JobStatus

from tests.db_helpers import make_sql_job_queue, open_test_database, seed_sql_pdf_document


@pytest.mark.asyncio
async def test_sql_enqueue_claim_and_complete() -> None:
    runtime = await open_test_database()
    queue = make_sql_job_queue(runtime, max_attempts=3)
    pdf_document_id = await seed_sql_pdf_document(runtime)

    await queue.enqueue(pdf_document_id=pdf_document_id, job_type="process_pdf")
    claimed = await queue.claim_next(worker_id="worker-a")
    assert claimed is not None
    assert claimed.pdf_document_id == pdf_document_id
    assert claimed.status == JobStatus.RUNNING

    await queue.complete(claimed.id)
    done = await queue.get_by_pdf_document_id(pdf_document_id)
    assert done.status == JobStatus.COMPLETED

    await runtime.close()


@pytest.mark.asyncio
async def test_sql_enqueue_is_idempotent_per_pdf_document_id() -> None:
    runtime = await open_test_database()
    queue = make_sql_job_queue(runtime)
    pdf_document_id = await seed_sql_pdf_document(runtime)

    first = await queue.enqueue(pdf_document_id=pdf_document_id, job_type="process_pdf")
    second = await queue.enqueue(pdf_document_id=pdf_document_id, job_type="process_pdf")
    assert second.id == first.id

    await runtime.close()


@pytest.mark.asyncio
async def test_sql_concurrent_claim_returns_distinct_jobs() -> None:
    runtime = await open_test_database()
    queue = make_sql_job_queue(runtime)
    pdf_a = await seed_sql_pdf_document(
        runtime,
        email="worker-a@example.com",
        storage_key="fixtures/a.pdf",
    )
    pdf_b = await seed_sql_pdf_document(
        runtime,
        email="worker-b@example.com",
        storage_key="fixtures/b.pdf",
    )
    await queue.enqueue(pdf_document_id=pdf_a, job_type="process_pdf")
    await queue.enqueue(pdf_document_id=pdf_b, job_type="process_pdf")

    claimed_a, claimed_b = await asyncio.gather(
        queue.claim_next(worker_id="worker-1"),
        queue.claim_next(worker_id="worker-2"),
    )

    assert claimed_a is not None
    assert claimed_b is not None
    assert claimed_a.id != claimed_b.id
    assert {claimed_a.pdf_document_id, claimed_b.pdf_document_id} == {pdf_a, pdf_b}

    await runtime.close()


@pytest.mark.asyncio
async def test_sql_release_stale_locks() -> None:
    runtime = await open_test_database()
    queue = make_sql_job_queue(runtime)
    pdf_document_id = await seed_sql_pdf_document(runtime)
    await queue.enqueue(pdf_document_id=pdf_document_id, job_type="process_pdf")
    claimed = await queue.claim_next(worker_id="worker-a")
    assert claimed is not None

    released = await queue.release_stale_locks(
        older_than=datetime.now(UTC) + timedelta(seconds=1),
    )
    assert released == 1

    updated = await queue.get_by_pdf_document_id(pdf_document_id)
    assert updated.status == JobStatus.PENDING

    await runtime.close()
