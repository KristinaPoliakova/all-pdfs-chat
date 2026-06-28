from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.exc import OperationalError

import app.infrastructure.persistence.sql.models as _db_models  # noqa: F401 - register ORM models with Base.metadata
from app.agent.tracing import configure_tracing
from app.api.router import api_router
from app.api.routes import health
from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.rate_limit import configure_rate_limiting
from app.infrastructure.factories.chat_checkpointer import (
    close_chat_checkpointer,
    init_chat_checkpointer,
)
from app.infrastructure.factories.jobs import create_job_queue, reset_job_queue_state
from app.infrastructure.factories.pdf import create_pdf_repository, reset_pdf_repository_state
from app.infrastructure.factories.sessions import (
    create_session_repository,
    reset_session_repository_state,
)
from app.infrastructure.factories.storage import reset_file_storage_state
from app.infrastructure.factories.users import create_user_repository, reset_user_repository_state
from app.infrastructure.persistence.sql.lifecycle import (
    close_database,
    get_database,
    init_database,
)
from app.infrastructure.persistence.sql.migrations import SchemaRevisionError
from app.infrastructure.persistence.sql.startup_errors import format_database_startup_error
from app.observability.http_tracing import (
    configure_http_tracing,
    instrument_fastapi_app,
    instrument_sqlalchemy_engine,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing(settings)

    try:
        await init_database()
    except OperationalError as exc:
        logger.error(format_database_startup_error(exc))
        raise
    except SchemaRevisionError as exc:
        logger.error("%s", exc)
        raise

    instrument_sqlalchemy_engine(get_database().engine)

    create_pdf_repository()
    create_job_queue()
    create_user_repository()
    create_session_repository()

    await init_chat_checkpointer(settings)

    fastapi_app.state.db_initialized = True
    fastapi_app.state.ready = True
    yield
    fastapi_app.state.ready = False
    await reset_session_repository_state()
    await reset_user_repository_state()
    await reset_job_queue_state()
    await reset_pdf_repository_state()
    reset_file_storage_state()
    await close_chat_checkpointer()
    await close_database()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="all-pdfs-chat", lifespan=lifespan)
    register_exception_handlers(app)
    configure_rate_limiting(app)

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

    Instrumentator(
        excluded_handlers=["^/health$", "^/ready$", "^/metrics$"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    # HTTP request tracing must be configured here, before instrumenting the app:
    # FastAPIInstrumentor adds ASGI middleware that can only be attached at
    # construction (not after startup), and instrument_fastapi_app no-ops unless
    # configure_http_tracing has already flipped the enabled flag. The SQLAlchemy
    # engine is instrumented later in lifespan, once the engine exists.
    configure_http_tracing(settings)
    instrument_fastapi_app(app)

    return app


app = create_app()
