from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(OperationalError)
    async def operational_error_handler(
        _request: Request,
        exc: OperationalError,
    ) -> JSONResponse:
        message = str(exc.orig) if exc.orig is not None else str(exc)
        logger.error("Database operational error: %s", message)
        if "readonly" in message.lower():
            detail = (
                "Database is read-only. Check PostgreSQL permissions and that DATABASE_URL "
                "points to a writable database."
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": detail},
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error"},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        _request: Request,
        exc: IntegrityError,
    ) -> JSONResponse:
        logger.warning("Database integrity error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "A record with this identifier already exists"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
