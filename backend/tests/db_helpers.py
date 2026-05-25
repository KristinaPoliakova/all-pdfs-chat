from __future__ import annotations

from app.infrastructure.persistence.sql.repositories.jobs import SqlJobQueue
from app.infrastructure.persistence.sql.repositories.pdf import SqlPdfRepository
from app.infrastructure.persistence.sql.repositories.sessions import SqlSessionRepository
from app.infrastructure.persistence.sql.repositories.users import SqlUserRepository
from app.infrastructure.persistence.sql.runtime import DatabaseRuntime


async def open_test_database(url: str = "sqlite+aiosqlite:///:memory:") -> DatabaseRuntime:
    runtime = DatabaseRuntime(url)
    await runtime.init_schema()
    return runtime


def make_sql_pdf_repository(runtime: DatabaseRuntime) -> SqlPdfRepository:
    return SqlPdfRepository(runtime.session_factory)


def make_sql_job_queue(runtime: DatabaseRuntime, *, max_attempts: int = 3) -> SqlJobQueue:
    return SqlJobQueue(runtime.session_factory, max_attempts=max_attempts)


def make_sql_user_repository(runtime: DatabaseRuntime) -> SqlUserRepository:
    return SqlUserRepository(runtime.session_factory)


def make_sql_session_repository(runtime: DatabaseRuntime) -> SqlSessionRepository:
    return SqlSessionRepository(runtime.session_factory)
