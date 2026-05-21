from pathlib import Path

import pytest
from app.metadata.sql import SqlPdfMetadataStore


@pytest.mark.asyncio
async def test_init_creates_parent_directory_for_sqlite_file(tmp_path: Path) -> None:
    db_file = tmp_path / "nested" / "app.db"

    store = SqlPdfMetadataStore(f"sqlite+aiosqlite:///{db_file}")
    await store.init()

    assert db_file.is_file()
    await store.close()


@pytest.mark.asyncio
async def test_sql_store_persists_metadata() -> None:
    store = SqlPdfMetadataStore("sqlite+aiosqlite:///:memory:")
    await store.init()

    record = await store.create(
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    assert record.filename == "doc.pdf"
    assert record.storage_key == "pdfs/uuid-doc.pdf"
    assert record.size_bytes == 100

    await store.close()
