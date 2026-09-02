from __future__ import annotations

from app.application.ports.jobs import JobQueue
from app.config.settings import Settings, get_settings
from app.infrastructure.persistence.sql.lifecycle import get_database
from app.infrastructure.persistence.sql.repositories.jobs import SqlJobQueue


def create_job_queue(settings: Settings | None = None) -> JobQueue:
    cfg = settings or get_settings()
    return SqlJobQueue(
        get_database(settings).session_factory,
        max_attempts=cfg.worker_max_attempts,
    )
