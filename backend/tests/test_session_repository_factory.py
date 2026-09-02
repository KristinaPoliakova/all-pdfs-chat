from unittest.mock import patch

import pytest
from app.config.settings import Settings
from app.infrastructure.factories.sessions import create_session_repository
from app.infrastructure.persistence.sql.repositories.sessions import SqlSessionRepository


@pytest.mark.asyncio
async def test_factory_builds_sql_session_repository() -> None:
    with patch("app.infrastructure.persistence.sql.lifecycle.get_settings") as get_settings:
        get_settings.return_value = Settings(app_env="dev", _env_file=None)
        repo = create_session_repository()

    assert isinstance(repo, SqlSessionRepository)
