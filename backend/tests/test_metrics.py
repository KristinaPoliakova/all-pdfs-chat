from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus_metrics(api_client: AsyncClient) -> None:
    # Hit an instrumented route first so the metric registry is populated.
    await api_client.get("/health")

    response = await api_client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_request_duration_seconds" in response.text


@pytest.mark.asyncio
async def test_metrics_endpoint_excludes_health_and_ready(api_client: AsyncClient) -> None:
    await api_client.get("/health")
    await api_client.get("/ready")

    response = await api_client.get("/metrics")

    # /health, /ready, /metrics are excluded from instrumentation (noise reduction):
    # no per-handler series should be emitted for them.
    assert 'handler="/health"' not in response.text
    assert 'handler="/ready"' not in response.text
    assert 'handler="/metrics"' not in response.text
