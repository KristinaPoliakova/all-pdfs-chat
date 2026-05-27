from __future__ import annotations

import importlib

import pytest
from app.infrastructure.persistence.sql.base import Base
from app.infrastructure.persistence.sql.repositories.jobs import SqlJobQueue
from app.infrastructure.persistence.sql.repositories.pdf import SqlPdfRepository
from app.infrastructure.persistence.sql.repositories.sessions import SqlSessionRepository
from app.infrastructure.persistence.sql.repositories.users import SqlUserRepository
from app.infrastructure.persistence.sql.runtime import DatabaseRuntime
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from tests.settings_helpers import TEST_DATABASE_URL


def _register_orm_models() -> None:
    importlib.import_module("app.infrastructure.persistence.sql.models")


async def truncate_sql_tables(runtime: DatabaseRuntime) -> None:
    """Clear app tables so SQL integration tests do not leak state."""
    _register_orm_models()
    table_names = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    if not table_names:
        return
    async with runtime.session_factory() as session:
        await session.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
        await session.commit()


async def open_test_database(url: str = TEST_DATABASE_URL) -> DatabaseRuntime:
    runtime = DatabaseRuntime(url)
    try:
        await runtime.init_schema()
        await truncate_sql_tables(runtime)
    except (OperationalError, OSError, ConnectionRefusedError) as exc:
        pytest.skip(f"PostgreSQL not available ({url}): {exc}")
    return runtime


def make_sql_pdf_repository(runtime: DatabaseRuntime) -> SqlPdfRepository:
    return SqlPdfRepository(runtime.session_factory)


def make_sql_job_queue(runtime: DatabaseRuntime, *, max_attempts: int = 3) -> SqlJobQueue:
    return SqlJobQueue(runtime.session_factory, max_attempts=max_attempts)


def make_sql_user_repository(runtime: DatabaseRuntime) -> SqlUserRepository:
    return SqlUserRepository(runtime.session_factory)


def make_sql_session_repository(runtime: DatabaseRuntime) -> SqlSessionRepository:
    return SqlSessionRepository(runtime.session_factory)


async def seed_sql_pdf_document(
    runtime: DatabaseRuntime,
    *,
    email: str = "jobs-test@example.com",
    storage_key: str = "fixtures/fixture.pdf",
) -> str:
    """Create a user and PDF row so job-queue FK constraints are satisfied."""
    users = make_sql_user_repository(runtime)
    user = await users.create(email=email, password_hash="hash")
    pdfs = make_sql_pdf_repository(runtime)
    record = await pdfs.create(
        user_id=user.id,
        filename="fixture.pdf",
        storage_key=storage_key,
        size_bytes=1,
    )
    return record.id


async def seed_sql_user_and_pdf(
    runtime: DatabaseRuntime,
    *,
    email: str = "sql-test@example.com",
    storage_key: str = "pdfs/sql-test.pdf",
) -> tuple[str, str]:
    """Return (user_id, pdf_document_id) with FK-safe rows."""
    users = make_sql_user_repository(runtime)
    user = await users.create(email=email, password_hash="hash")
    pdfs = make_sql_pdf_repository(runtime)
    record = await pdfs.create(
        user_id=user.id,
        filename="doc.pdf",
        storage_key=storage_key,
        size_bytes=100,
    )
    return user.id, record.id
