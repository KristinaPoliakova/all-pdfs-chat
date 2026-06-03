from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from app.api.deps import get_file_storage, get_job_queue, get_pdf_repository
from app.application.auth.deps import get_session_repository, get_user_repository
from app.config.settings import Settings, get_settings
from app.core.rate_limit import limiter
from app.main import create_app
from httpx import ASGITransport, AsyncClient

from tests.settings_helpers import TEST_DATABASE_URL


@pytest.fixture(autouse=True)
def _reset_limiter_storage() -> None:
    limiter.reset()
    yield
    limiter.reset()


@pytest.mark.asyncio
async def test_rate_limits_disabled_in_dev(api_client: AsyncClient) -> None:
    for _ in range(8):
        response = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"},
        )
        assert response.status_code in {401, 422}
        assert response.status_code != 429


@pytest.fixture
async def prod_rate_limited_client(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    file_storage,
    pdf_repository,
    job_queue,
    user_repository,
    session_repository,
) -> AsyncIterator[AsyncClient]:
    get_settings.cache_clear()

    def _get_prod_settings():
        return Settings(
            app_env="prod",
            database_url=TEST_DATABASE_URL,
            _env_file=None,
            rate_limit_enabled=True,
        )

    async def _skip_init_database(settings=None) -> None:
        return None

    monkeypatch.setattr("app.main.init_database", _skip_init_database)
    monkeypatch.setattr("app.main.get_settings", _get_prod_settings)
    monkeypatch.setattr("app.config.settings.get_settings", _get_prod_settings)
    monkeypatch.setattr("app.core.rate_limit.app_settings.get_settings", _get_prod_settings)
    monkeypatch.setattr(
        "app.infrastructure.persistence.sql.lifecycle.get_settings",
        _get_prod_settings,
    )
    monkeypatch.setattr("app.infrastructure.factories.jobs.get_settings", _get_prod_settings)
    monkeypatch.setattr(
        "app.infrastructure.factories.storage.get_settings",
        _get_prod_settings,
    )

    app = create_app()
    app.dependency_overrides[get_settings] = _get_prod_settings
    app.dependency_overrides[get_file_storage] = lambda: file_storage
    app.dependency_overrides[get_pdf_repository] = lambda: pdf_repository
    app.dependency_overrides[get_job_queue] = lambda: job_queue
    app.dependency_overrides[get_user_repository] = lambda: user_repository
    app.dependency_overrides[get_session_repository] = lambda: session_repository

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_login_rate_limit_returns_429_in_prod(
    prod_rate_limited_client: AsyncClient,
) -> None:
    client = prod_rate_limited_client
    assert limiter.enabled is True
    headers = {"X-Forwarded-For": "203.0.113.50"}

    register = await client.post(
        "/api/v1/auth/register",
        json={"email": "ratelimit@example.com", "password": "secret123"},
        headers=headers,
    )
    assert register.status_code == 201

    statuses: list[int] = []
    for _ in range(6):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "ratelimit@example.com", "password": "secret123"},
            headers=headers,
        )
        statuses.append(response.status_code)

    assert statuses[:5] == [200, 200, 200, 200, 200]
    assert statuses[5] == 429
    blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit@example.com", "password": "secret123"},
        headers=headers,
    )
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Rate limit exceeded"}
    assert "Retry-After" in blocked.headers


@pytest.mark.asyncio
async def test_health_unaffected_by_rate_limit(
    prod_rate_limited_client: AsyncClient,
) -> None:
    client = prod_rate_limited_client
    headers = {"X-Forwarded-For": "203.0.113.99"}

    for _ in range(6):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "wrong"},
            headers=headers,
        )

    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
