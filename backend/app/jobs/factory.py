from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.db.lifecycle import get_database
from app.db.repositories.jobs import SqlJobQueue
from app.jobs.protocol import JobQueue

_queue: JobQueue | None = None


def create_job_queue(settings: Settings | None = None) -> JobQueue:
    global _queue
    cfg = settings or get_settings()
    if settings is not None:
        return SqlJobQueue(
            get_database(settings).session_factory,
            max_attempts=cfg.worker_max_attempts,
        )

    if _queue is None:
        _queue = SqlJobQueue(
            get_database().session_factory,
            max_attempts=cfg.worker_max_attempts,
        )
    return _queue


async def reset_job_queue_state() -> None:
    global _queue
    _queue = None
