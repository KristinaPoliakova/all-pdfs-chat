from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401
from app.api.router import api_router
from app.api.routes import health
from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.db.sqlite_paths import ensure_sqlite_writable
from app.jobs.factory import create_job_queue, reset_job_queue_state
from app.metadata.factory import create_pdf_metadata_store, reset_metadata_store_state
from app.storage.factory import reset_file_storage_state


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    if settings.is_dev:
        ensure_sqlite_writable(settings.database_url)

    metadata_store = create_pdf_metadata_store()
    await metadata_store.init()
    job_queue = create_job_queue()
    await job_queue.init()
    app.state.ready = True
    yield
    app.state.ready = False
    await job_queue.close()
    await reset_job_queue_state()
    await reset_metadata_store_state()
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
