from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

import app.db.models  # noqa: F401 - register ORM models with Base.metadata
from app.api.router import api_router
from app.api.routes import health
from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.db.sqlite_paths import ensure_sqlite_writable
from app.db.startup_errors import format_database_startup_error
from app.jobs.factory import create_job_queue, reset_job_queue_state
from app.pdf_repository.factory import create_pdf_repository, reset_pdf_repository_state
from app.storage.factory import reset_file_storage_state

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    if settings.is_dev:
        ensure_sqlite_writable(settings.database_url)

    pdf_repository = create_pdf_repository()
    try:
        await pdf_repository.init()
        job_queue = create_job_queue()
        await job_queue.init()
    except OperationalError as exc:
        logger.error(format_database_startup_error(exc))
        raise
    app.state.ready = True
    yield
    app.state.ready = False
    await job_queue.close()
    await reset_job_queue_state()
    await reset_pdf_repository_state()
    reset_file_storage_state()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="all-pdfs-chat", lifespan=lifespan)
    register_exception_handlers(app)

    origins = settings.cors_origin_list
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health.router)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
