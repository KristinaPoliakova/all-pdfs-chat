from unittest.mock import patch

import pytest
from app.config.settings import Settings
from app.db.repositories.sessions import SqlSessionRepository
from app.session_repository.factory import create_session_repository, reset_session_repository_state


@pytest.fixture(autouse=True)
async def _reset_factory() -> None:
    await reset_session_repository_state()
    yield
    await reset_session_repository_state()


@pytest.mark.asyncio
async def test_factory_returns_cached_singleton() -> None:
    with patch("app.db.lifecycle.get_settings") as get_settings:
        get_settings.return_value = Settings(app_env="dev", _env_file=None)
        first = create_session_repository()
        second = create_session_repository()

    assert first is second
    assert isinstance(first, SqlSessionRepository)
