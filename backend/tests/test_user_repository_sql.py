from pathlib import Path

import pytest

from tests.db_helpers import make_sql_user_repository, open_test_database


@pytest.mark.asyncio
async def test_init_creates_parent_directory_for_sqlite_file(tmp_path: Path) -> None:
    db_file = tmp_path / "nested" / "app.db"

    runtime = await open_test_database(f"sqlite+aiosqlite:///{db_file}")

    assert db_file.is_file()
    await runtime.close()


@pytest.mark.asyncio
async def test_create_and_get_by_email() -> None:
    runtime = await open_test_database()
    repo = make_sql_user_repository(runtime)

    created = await repo.create(email="Alice@Example.com", password_hash="hash")
    found = await repo.get_by_email("alice@example.com")

    assert found == created
    assert await repo.get(created.id) == created

    await runtime.close()
