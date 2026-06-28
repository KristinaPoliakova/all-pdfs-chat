from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_ROOT / ".env"
DEFAULT_LOCAL_STORAGE_PATH = (_BACKEND_ROOT / "data" / "uploads").resolve()
# Backwards-compatible alias used by tests and existing imports.
LOCAL_STORAGE_PATH = DEFAULT_LOCAL_STORAGE_PATH
DEFAULT_DEV_DATABASE_URL = (
    "postgresql+asyncpg://all_pdfs_chat:devpassword@127.0.0.1:5432/all_pdfs_chat"
)
_MIN_UPLOAD_SIZE_BYTES = 1
_MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024
MAX_FILENAME_LENGTH = 255
_STORAGE_BACKENDS = frozenset({"local", "azure"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"
    database_url: str = DEFAULT_DEV_DATABASE_URL
    storage_backend: str = "local"
    local_storage_path: str = ""
    max_upload_size_bytes: int = 10 * 1024 * 1024
    azure_storage_connection_string: str = ""
    azure_storage_container_name: str = "pdfs"
    cors_allowed_origins: str = ""
    log_level: str = "INFO"
    classification_enabled: bool = True
    classification_max_pages: int = 10
    worker_poll_interval_seconds: float = 1.0
    worker_lock_ttl_seconds: int = 300
    worker_max_attempts: int = 3
    parsing_enabled: bool = False
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_api_key: str = ""
    parsing_poll_interval_seconds: float = 2.0
    parsing_max_wait_seconds: int = 600
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    agent_search_top_k: int = 4
    agent_max_tool_iterations: int = 5
    agent_timeout_seconds: int = 60
    agent_tool_char_limit: int = 6000
    tracing_enabled: bool = False
    mlflow_tracking_uri: str = ""
    mlflow_experiment: str = "all-pdfs-chat-agent"
    request_tracing_enabled: bool = False
    request_trace_sample_ratio: float = 1.0
    mlflow_http_experiment: str = "all-pdfs-chat-http"
    session_ttl_seconds: int = 7 * 24 * 3600
    rate_limit_enabled: bool = True
    rate_limit_auth_register: str = "5/minute"
    rate_limit_auth_login: str = "5/minute"
    rate_limit_auth_logout: str = "30/minute"
    rate_limit_auth_me: str = "60/minute"
    rate_limit_pdf_upload: str = "10/hour"
    rate_limit_pdf_read: str = "60/minute"

    @property
    def rate_limits_active(self) -> bool:
        return self.is_prod and self.rate_limit_enabled

    @property
    def is_prod(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}

    @property
    def is_dev(self) -> bool:
        return self.app_env.strip().lower() in {"dev", "development"}

    @property
    def resolved_local_storage_path(self) -> Path:
        override = self.local_storage_path.strip()
        if override:
            return Path(override).expanduser().resolve()
        return DEFAULT_LOCAL_STORAGE_PATH

    @property
    def uses_local_storage(self) -> bool:
        return self.is_dev or self.storage_backend == "local"

    @property
    def uses_azure_storage(self) -> bool:
        return self.is_prod and self.storage_backend == "azure"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        url = value.strip()
        if not url:
            raise ValueError("DATABASE_URL must not be empty")
        if not url.lower().startswith("postgresql+"):
            raise ValueError(
                "DATABASE_URL must use a PostgreSQL async driver (postgresql+asyncpg://...)",
            )
        return url

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

    @field_validator("storage_backend")
    @classmethod
    def validate_storage_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _STORAGE_BACKENDS:
            msg = f"STORAGE_BACKEND must be one of: {', '.join(sorted(_STORAGE_BACKENDS))}"
            raise ValueError(msg)
        return normalized

    @model_validator(mode="after")
    def validate_environment(self) -> Self:
        if not self.is_dev and not self.is_prod:
            raise ValueError(f"Unknown APP_ENV: {self.app_env!r}. Expected dev or prod.")

        if self.is_prod:
            missing: list[str] = []
            if self.uses_azure_storage and not self.azure_storage_connection_string.strip():
                missing.append("AZURE_STORAGE_CONNECTION_STRING")
            if self.parsing_enabled and not self.azure_document_intelligence_endpoint.strip():
                missing.append("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            if missing:
                raise ValueError(f"Required when APP_ENV=prod: {', '.join(missing)}")

        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
