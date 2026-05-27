from __future__ import annotations

import logging

from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


def format_database_startup_error(exc: OperationalError) -> str:
    message = str(exc.orig) if exc.orig is not None else str(exc)
    lowered = message.lower()
    if "connection refused" in lowered or "could not connect" in lowered:
        return (
            "PostgreSQL connection refused during startup. "
            "Ensure the database is running (local: docker compose up -d postgres) "
            "and DATABASE_URL host/port match. "
            f"Driver error: {message}"
        )
    if "password authentication failed" in lowered:
        return (
            "PostgreSQL authentication failed during startup. "
            "Check DATABASE_URL username and password. "
            f"Driver error: {message}"
        )
    if "does not exist" in lowered and "database" in lowered:
        return (
            "PostgreSQL database not found during startup. "
            "Create the database or fix DATABASE_URL. "
            f"Driver error: {message}"
        )
    if "ssl" in lowered and (
        "required" in lowered or "certificate" in lowered or "handshake" in lowered
    ):
        return (
            "PostgreSQL SSL connection failed during startup. "
            "Add sslmode to DATABASE_URL (e.g. sslmode=require for managed Postgres). "
            f"Driver error: {message}"
        )
    return f"Database startup failed: {message}"
