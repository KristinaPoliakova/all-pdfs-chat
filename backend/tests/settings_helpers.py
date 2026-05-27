from __future__ import annotations

from app.config.settings import Settings

TEST_DATABASE_URL = (
    "postgresql+asyncpg://all_pdfs_chat:devpassword@127.0.0.1:5432/all_pdfs_chat_test"
)


def make_test_settings(**overrides: object) -> Settings:
    """Build Settings isolated from developer .env and shell exports."""
    return Settings(
        app_env="dev",
        database_url=TEST_DATABASE_URL,
        _env_file=None,
        **overrides,
    )
