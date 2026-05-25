from pathlib import Path
from unittest.mock import patch

import app.infrastructure.persistence.sql.models as _db_models  # noqa: F401
import pytest
from app.config.settings import Settings
from app.infrastructure.persistence.sql.lifecycle import (
    close_database,
    get_database,
    init_database,
    reset_database_state,
)
from app.infrastructure.persistence.sql.models.user import User
from app.infrastructure.persistence.sql.runtime import DatabaseRuntime


@pytest.fixture(autouse=True)
async def _reset_database() -> None:
    await reset_database_state()
    yield
    await reset_database_state()


@pytest.mark.asyncio
async def test_init_schema_creates_sqlite_file(tmp_path: Path) -> None:
    db_file = tmp_path / "nested" / "app.db"
    runtime = DatabaseRuntime(f"sqlite+aiosqlite:///{db_file}")

    await runtime.init_schema()

    assert db_file.is_file()
    await runtime.close()


@pytest.mark.asyncio
async def test_init_schema_registers_all_tables() -> None:
    runtime = DatabaseRuntime("sqlite+aiosqlite:///:memory:")
    await runtime.init_schema()

    async with runtime.session_factory() as session:
        session.add(User(email="alice@example.com", password_hash="hash"))
        await session.commit()

    await runtime.close()


@pytest.mark.asyncio
async def test_get_database_singleton() -> None:
    with patch("app.infrastructure.persistence.sql.lifecycle.get_settings") as get_settings:
        get_settings.return_value = Settings(app_env="dev", _env_file=None)
        first = get_database()
        second = get_database()

    assert first is second


@pytest.mark.asyncio
async def test_get_database_with_settings_returns_ephemeral_runtime() -> None:
    settings = Settings(app_env="dev", _env_file=None)

    runtime = get_database(settings)

    assert isinstance(runtime, DatabaseRuntime)
    with patch("app.infrastructure.persistence.sql.lifecycle.get_settings") as get_settings:
        get_settings.return_value = Settings(app_env="dev", _env_file=None)
        assert get_database() is not runtime


@pytest.mark.asyncio
async def test_init_database_initializes_process_singleton() -> None:
    with patch("app.infrastructure.persistence.sql.lifecycle.get_settings") as get_settings:
        get_settings.return_value = Settings(app_env="dev", _env_file=None)
        await init_database()

        runtime = get_database()
        async with runtime.session_factory() as session:
            session.add(User(email="bob@example.com", password_hash="hash"))
            await session.commit()

    await close_database()
