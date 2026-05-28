from __future__ import annotations

from unittest.mock import patch

import pytest
from app.application.ports.jobs import JobStatus
from app.infrastructure.persistence.sql.migrations import (
    SchemaRevisionError,
    downgrade_to_base,
    ensure_migrated,
    ensure_schema_current,
    get_current_revision,
    get_head_revision,
)
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from tests.db_helpers import (
    make_sql_job_queue,
    make_sql_pdf_repository,
    make_sql_user_repository,
    open_test_database,
    seed_sql_full_document_graph,
)
from tests.settings_helpers import TEST_DATABASE_URL


def _list_app_table_names(database_url: str) -> list[str]:
    from app.infrastructure.persistence.sql.migrations import to_sync_database_url
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    engine = create_engine(to_sync_database_url(database_url), poolclass=NullPool)
    try:
        with engine.connect() as connection:
            return sorted(
                connection.execute(
                    text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
                    )
                ).scalars()
            )
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_upgrade_head_on_empty_database() -> None:
    try:
        ensure_migrated(TEST_DATABASE_URL)
    except (OperationalError, OSError, ConnectionRefusedError) as exc:
        pytest.skip(f"PostgreSQL not available: {exc}")

    runtime = await open_test_database()
    try:
        async with runtime.session_factory() as session:
            tables = (
                (
                    await session.execute(
                        text(
                            "SELECT tablename FROM pg_tables "
                            "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
                        )
                    )
                )
                .scalars()
                .all()
            )
        assert sorted(tables) == sorted(
            [
                "pdf_documents",
                "pdf_jobs",
                "pdf_page_extracts",
                "pdf_pages",
                "user_sessions",
                "users",
            ]
        )
        assert get_current_revision(TEST_DATABASE_URL) == get_head_revision()
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_downgrade_initial_removes_app_tables() -> None:
    try:
        ensure_migrated(TEST_DATABASE_URL)
    except (OperationalError, OSError, ConnectionRefusedError) as exc:
        pytest.skip(f"PostgreSQL not available: {exc}")

    try:
        downgrade_to_base(TEST_DATABASE_URL)
        assert _list_app_table_names(TEST_DATABASE_URL) == []
        assert get_current_revision(TEST_DATABASE_URL) is None
    finally:
        ensure_migrated(TEST_DATABASE_URL)


@pytest.mark.asyncio
async def test_schema_supports_full_fk_insert_roundtrip() -> None:
    runtime = await open_test_database()
    try:
        user_id, pdf_id = await seed_sql_full_document_graph(runtime)
        users = make_sql_user_repository(runtime)
        pdfs = make_sql_pdf_repository(runtime)
        jobs = make_sql_job_queue(runtime)

        assert await users.get(user_id) is not None
        assert await pdfs.get(pdf_id) is not None

        pages = await pdfs.get_pages(pdf_id)
        assert len(pages) == 1
        assert pages[0].page_number == 1

        extracts = await pdfs.get_page_extracts(pdf_id)
        assert len(extracts) == 1
        assert extracts[0].content_text == "migration test extract"

        job = await jobs.get_by_pdf_document_id(pdf_id)
        assert job.pdf_document_id == pdf_id
        assert job.status == JobStatus.PENDING
    finally:
        await runtime.close()


def test_ensure_schema_current_raises_in_strict_mode_when_stale() -> None:
    with (
        patch(
            "app.infrastructure.persistence.sql.migrations.get_head_revision",
            return_value="head",
        ),
        patch(
            "app.infrastructure.persistence.sql.migrations.get_current_revision",
            return_value="stale",
        ),
    ):
        with pytest.raises(SchemaRevisionError, match="Alembic head"):
            ensure_schema_current(database_url=TEST_DATABASE_URL, strict=True)


@pytest.mark.asyncio
async def test_ensure_schema_current_passes_when_at_head() -> None:
    try:
        ensure_migrated(TEST_DATABASE_URL)
    except (OperationalError, OSError, ConnectionRefusedError) as exc:
        pytest.skip(f"PostgreSQL not available: {exc}")

    ensure_schema_current(database_url=TEST_DATABASE_URL, strict=True)
