from pathlib import Path

import pytest

from tests.db_helpers import make_sql_pdf_repository, open_test_database


@pytest.mark.asyncio
async def test_init_creates_parent_directory_for_sqlite_file(tmp_path: Path) -> None:
    db_file = tmp_path / "nested" / "app.db"

    runtime = await open_test_database(f"sqlite+aiosqlite:///{db_file}")

    assert db_file.is_file()
    await runtime.close()


@pytest.mark.asyncio
async def test_sql_store_persists_metadata() -> None:
    runtime = await open_test_database()
    store = make_sql_pdf_repository(runtime)

    record = await store.create(
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    assert record.filename == "doc.pdf"
    assert record.storage_key == "pdfs/uuid-doc.pdf"
    assert record.size_bytes == 100

    await runtime.close()
