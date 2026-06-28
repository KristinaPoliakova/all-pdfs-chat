from __future__ import annotations

import json
import urllib.error
from collections.abc import Iterator

import app.observability.http_tracing as http_tracing
import pytest
from fastapi import FastAPI

from tests.settings_helpers import make_test_settings


@pytest.fixture(autouse=True)
def _reset_flag() -> Iterator[None]:
    http_tracing._enabled = False
    yield
    http_tracing._enabled = False


def test_disabled_by_default() -> None:
    http_tracing.configure_http_tracing(make_test_settings(request_tracing_enabled=False))
    assert http_tracing._enabled is False


def test_enabled_without_uri_stays_disabled() -> None:
    http_tracing.configure_http_tracing(
        make_test_settings(request_tracing_enabled=True, mlflow_tracking_uri="")
    )
    assert http_tracing._enabled is False


def test_setup_error_is_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the setup body to raise and confirm it never propagates.
    monkeypatch.setattr(http_tracing, "_build_provider", _raise)
    http_tracing.configure_http_tracing(
        make_test_settings(
            request_tracing_enabled=True, mlflow_tracking_uri="http://localhost:5001"
        )
    )
    assert http_tracing._enabled is False


def test_success_path_enables_tracing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Stub the provider build and the SDK calls so nothing touches the network
    # or mutates global OTel state, then confirm the success branch flips the flag.
    monkeypatch.setattr(http_tracing, "_build_provider", lambda settings, uri: object())
    monkeypatch.setattr("opentelemetry.trace.set_tracer_provider", lambda provider: None)
    monkeypatch.setattr(
        "opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor.instrument",
        lambda self, *args, **kwargs: None,
    )

    http_tracing.configure_http_tracing(
        make_test_settings(
            request_tracing_enabled=True, mlflow_tracking_uri="http://localhost:5001"
        )
    )

    assert http_tracing._enabled is True


def test_sample_ratio_is_clamped() -> None:
    assert http_tracing._clamp_ratio(5.0) == 1.0
    assert http_tracing._clamp_ratio(-1.0) == 0.0
    assert http_tracing._clamp_ratio(0.25) == 0.25


def test_current_http_trace_id_returns_none_when_disabled() -> None:
    http_tracing._enabled = False
    assert http_tracing.current_http_trace_id() is None


def test_current_http_trace_id_returns_hex_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    trace_id = 0x0123456789ABCDEF0123456789ABCDEF
    http_tracing._enabled = True
    monkeypatch.setattr(
        "opentelemetry.trace.get_current_span",
        lambda: _FakeSpan(_FakeSpanContext(is_valid=True, trace_id=trace_id)),
    )

    result = http_tracing.current_http_trace_id()

    assert result == format(trace_id, "032x")
    assert result is not None
    assert len(result) == 32


def test_instrument_fastapi_app_is_noop_when_disabled() -> None:
    http_tracing._enabled = False
    assert http_tracing.instrument_fastapi_app(FastAPI()) is None


def test_instrument_sqlalchemy_engine_is_noop_when_disabled() -> None:
    http_tracing._enabled = False
    assert http_tracing.instrument_sqlalchemy_engine(object()) is None


def test_resolve_http_experiment_id_returns_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: HTTP setup must resolve the experiment id WITHOUT mlflow.set_experiment
    # (which would hijack the agent pipeline's destination). It uses the REST API instead.
    urls: list[str] = []

    def fake_urlopen(url: object, timeout: float | None = None) -> _FakeHttpResponse:
        urls.append(url if isinstance(url, str) else url.full_url)
        return _FakeHttpResponse({"experiment": {"experiment_id": "42"}})

    monkeypatch.setattr(http_tracing.urllib.request, "urlopen", fake_urlopen)

    exp_id = http_tracing._resolve_http_experiment_id("http://localhost:5001", "all-pdfs-chat-http")

    assert exp_id == "42"
    assert len(urls) == 1
    assert "experiments/get-by-name" in urls[0]


def test_resolve_http_experiment_id_creates_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_urlopen(url: object, timeout: float | None = None) -> _FakeHttpResponse:
        full = url if isinstance(url, str) else url.full_url
        seen.append(full)
        if "get-by-name" in full:
            raise urllib.error.HTTPError(full, 404, "missing", hdrs=None, fp=None)
        return _FakeHttpResponse({"experiment_id": "99"})

    monkeypatch.setattr(http_tracing.urllib.request, "urlopen", fake_urlopen)

    exp_id = http_tracing._resolve_http_experiment_id("http://localhost:5001", "all-pdfs-chat-http")

    assert exp_id == "99"
    assert any("experiments/create" in u for u in seen)


class _FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeHttpResponse:
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


class _FakeSpanContext:
    def __init__(self, *, is_valid: bool, trace_id: int) -> None:
        self.is_valid = is_valid
        self.trace_id = trace_id


class _FakeSpan:
    def __init__(self, context: _FakeSpanContext) -> None:
        self._context = context

    def get_span_context(self) -> _FakeSpanContext:
        return self._context


def _raise(*args: object, **kwargs: object) -> object:
    raise RuntimeError("boom")
