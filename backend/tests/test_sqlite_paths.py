from app.config.settings import _BACKEND_ROOT, Settings
from app.infrastructure.persistence.sql.sqlite_paths import (
    is_sqlite_database_url,
    resolve_sqlite_database_url,
    sqlite_file_path,
)


def test_is_sqlite_database_url() -> None:
    assert is_sqlite_database_url("sqlite+aiosqlite:///./data/app.db") is True
    assert is_sqlite_database_url("postgresql+asyncpg://localhost/db") is False


def test_resolve_sqlite_database_url_anchors_relative_path_to_backend_root() -> None:
    resolved = resolve_sqlite_database_url(
        "sqlite+aiosqlite:///./data/app.db",
        base_dir=_BACKEND_ROOT,
    )

    assert resolved.startswith("sqlite+aiosqlite:///")
    assert sqlite_file_path(resolved) == (_BACKEND_ROOT / "data" / "app.db").resolve()


def test_settings_resolves_dev_database_url_to_absolute_path() -> None:
    settings = Settings(
        app_env="dev",
        database_url="sqlite+aiosqlite:///./data/app.db",
        _env_file=None,
    )

    assert sqlite_file_path(settings.database_url) == (_BACKEND_ROOT / "data" / "app.db").resolve()
