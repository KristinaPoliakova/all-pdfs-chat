from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(api_client: AsyncClient) -> None:
    response = await api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_returns_ready_when_app_started(api_client: AsyncClient) -> None:
    response = await api_client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
