from unittest.mock import patch

import pytest
from app.config.settings import _BACKEND_ROOT, Settings
from app.db.lifecycle import get_database
from app.db.repositories.users import SqlUserRepository
from app.db.sqlite_paths import sqlite_file_path
from app.user_repository.factory import create_user_repository, reset_user_repository_state


@pytest.fixture(autouse=True)
async def _reset_factory() -> None:
    await reset_user_repository_state()
    yield
    await reset_user_repository_state()


@pytest.mark.asyncio
async def test_factory_uses_sqlite_url_for_dev() -> None:
    settings = Settings(
        app_env="dev",
        database_url="sqlite+aiosqlite:///./test-dev-users.db",
        _env_file=None,
    )

    repo = create_user_repository(settings)

    assert isinstance(repo, SqlUserRepository)
    assert (
        sqlite_file_path(get_database(settings).database_url)
        == (_BACKEND_ROOT / "test-dev-users.db").resolve()
    )


@pytest.mark.asyncio
async def test_factory_returns_cached_singleton() -> None:
    with patch("app.db.lifecycle.get_settings") as get_settings:
        get_settings.return_value = Settings(app_env="dev", _env_file=None)
        first = create_user_repository()
        second = create_user_repository()

    assert first is second
