from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_ROOT / ".env"
LOCAL_STORAGE_PATH = Path("data/uploads")
_MIN_UPLOAD_SIZE_BYTES = 1
_MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024
MAX_FILENAME_LENGTH = 255


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    azure_sql_database_url: str = ""
    max_upload_size_bytes: int = 10 * 1024 * 1024
    azure_storage_connection_string: str = ""
    azure_storage_container_name: str = "pdfs"
    cors_allowed_origins: str = ""
    log_level: str = "INFO"

    @property
    def is_prod(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}

    @property
    def is_dev(self) -> bool:
        return self.app_env.strip().lower() in {"dev", "development"}

    @field_validator("max_upload_size_bytes")
    @classmethod
    def validate_max_upload_size(cls, value: int) -> int:
        if value < _MIN_UPLOAD_SIZE_BYTES or value > _MAX_UPLOAD_SIZE_BYTES:
            msg = (
                f"MAX_UPLOAD_SIZE_BYTES must be between {_MIN_UPLOAD_SIZE_BYTES} "
                f"and {_MAX_UPLOAD_SIZE_BYTES}"
            )
            raise ValueError(msg)
        return value

    @field_validator("azure_storage_container_name")
    @classmethod
    def validate_container_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("AZURE_STORAGE_CONTAINER_NAME must not be empty")
        return name

    @model_validator(mode="after")
    def validate_environment(self) -> Self:
        if not self.is_dev and not self.is_prod:
            raise ValueError(f"Unknown APP_ENV: {self.app_env!r}. Expected dev or prod.")

        if self.is_prod:
            missing: list[str] = []
            if not self.azure_storage_connection_string.strip():
                missing.append("AZURE_STORAGE_CONNECTION_STRING")
            if not self.azure_sql_database_url.strip():
                missing.append("AZURE_SQL_DATABASE_URL")
            if missing:
                raise ValueError(f"Required when APP_ENV=prod: {', '.join(missing)}")

        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
