from __future__ import annotations

import asyncio
import logging
import os
import signal
import socket

from app.classification.service import PdfClassificationService
from app.config.settings import get_settings
from app.core.logging import configure_logging
from app.infrastructure.factories.jobs import create_job_queue, reset_job_queue_state
from app.infrastructure.factories.pdf import create_pdf_repository, reset_pdf_repository_state
from app.infrastructure.factories.storage import create_file_storage, reset_file_storage_state
from app.infrastructure.persistence.sql.lifecycle import close_database, init_database
from app.parsing.factory import create_document_parser
from app.worker.pdf_pipeline import PdfProcessingPipeline

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    await init_database()
    pdf_repository = create_pdf_repository()
    job_queue = create_job_queue()
    storage = create_file_storage()
    classifier = PdfClassificationService(settings=settings)
    parser = create_document_parser(settings)
    pipeline = PdfProcessingPipeline(
        pdf_repository=pdf_repository,
        storage=storage,
        settings=settings,
        classifier=classifier,
        parser=parser,
    )

    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    stopping = asyncio.Event()

    def _request_stop(*_: object) -> None:
        stopping.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _request_stop)

    from datetime import UTC, datetime, timedelta

    logger.info("PDF worker started id=%s", worker_id)
    try:
        while not stopping.is_set():
            stale_before = datetime.now(UTC) - timedelta(seconds=settings.worker_lock_ttl_seconds)
            released = await job_queue.release_stale_locks(older_than=stale_before)
            if released:
                logger.warning(
                    "Released stale job locks count=%d older_than=%s",
                    released,
                    stale_before.isoformat(),
                )
            job = await job_queue.claim_next(worker_id=worker_id)
            if job is None:
                try:
                    await asyncio.wait_for(
                        stopping.wait(),
                        timeout=settings.worker_poll_interval_seconds,
                    )
                except TimeoutError:
                    pass
                continue
            try:
                await pipeline.run(job.pdf_id)
                await job_queue.complete(job.id)
            except Exception as exc:
                next_attempt = job.attempts + 1
                will_retry = next_attempt < job.max_attempts
                logger.exception(
                    "PDF job failed job_id=%s pdf_id=%s attempt=%d/%d will_retry=%s: %s",
                    job.id,
                    job.pdf_id,
                    next_attempt,
                    job.max_attempts,
                    will_retry,
                    exc,
                )
                await job_queue.fail_or_retry(job.id, error=str(exc))
    finally:
        await reset_job_queue_state()
        await reset_pdf_repository_state()
        reset_file_storage_state()
        await close_database()
        logger.info("PDF worker stopped id=%s", worker_id)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
