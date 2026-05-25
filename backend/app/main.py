from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

import app.infrastructure.persistence.sql.models as _db_models  # noqa: F401 - register ORM models with Base.metadata
from app.api.router import api_router
from app.api.routes import health
from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.infrastructure.factories.jobs import create_job_queue, reset_job_queue_state
from app.infrastructure.factories.pdf import create_pdf_repository, reset_pdf_repository_state
from app.infrastructure.factories.sessions import (
    create_session_repository,
    reset_session_repository_state,
)
from app.infrastructure.factories.storage import reset_file_storage_state
from app.infrastructure.factories.users import create_user_repository, reset_user_repository_state
from app.infrastructure.persistence.sql.lifecycle import close_database, init_database
from app.infrastructure.persistence.sql.startup_errors import format_database_startup_error

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    try:
        await init_database()
    except OperationalError as exc:
        logger.error(format_database_startup_error(exc))
        raise

    create_pdf_repository()
    create_job_queue()
    create_user_repository()
    create_session_repository()

    fastapi_app.state.ready = True
    yield
    fastapi_app.state.ready = False
    await reset_session_repository_state()
    await reset_user_repository_state()
    await reset_job_queue_state()
    await reset_pdf_repository_state()
    reset_file_storage_state()
    await close_database()


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
