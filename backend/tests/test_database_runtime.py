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
from app.infrastructure.persistence.sql.migrations import SchemaRevisionError, ensure_migrated
from app.infrastructure.persistence.sql.models.user import User
from app.infrastructure.persistence.sql.runtime import DatabaseRuntime
from sqlalchemy.exc import OperationalError

from tests.db_helpers import open_test_database
from tests.settings_helpers import TEST_DATABASE_URL


@pytest.fixture(autouse=True)
async def _reset_database() -> None:
    await reset_database_state()
    yield
    await reset_database_state()


@pytest.mark.asyncio
async def test_migrated_schema_accepts_user_insert() -> None:
    runtime = await open_test_database()

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
async def test_init_database_verifies_connection_when_schema_is_current() -> None:
    try:
        ensure_migrated(TEST_DATABASE_URL)
    except (OperationalError, OSError, ConnectionRefusedError) as exc:
        pytest.skip(f"PostgreSQL not available: {exc}")

    with patch("app.infrastructure.persistence.sql.lifecycle.get_settings") as get_settings:
        get_settings.return_value = Settings(
            app_env="dev",
            database_url=TEST_DATABASE_URL,
            _env_file=None,
        )
        await init_database()

        runtime = get_database()
        async with runtime.session_factory() as session:
            session.add(User(email="bob@example.com", password_hash="hash"))
            await session.commit()

    await close_database()


@pytest.mark.asyncio
async def test_init_database_raises_in_prod_when_schema_is_stale() -> None:
    with patch("app.infrastructure.persistence.sql.lifecycle.get_settings") as get_settings:
        get_settings.return_value = Settings(
            app_env="prod",
            database_url=TEST_DATABASE_URL,
            _env_file=None,
        )
        with patch(
            "app.infrastructure.persistence.sql.lifecycle.ensure_schema_current",
            side_effect=SchemaRevisionError("stale"),
        ):
            with pytest.raises(SchemaRevisionError, match="stale"):
                await init_database()
