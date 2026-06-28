from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from fastapi import FastAPI

from app.config.settings import Settings

logger = logging.getLogger(__name__)

_enabled = False
_SERVICE_NAME = "all-pdfs-chat-api"
# FastAPIInstrumentor matches these as substrings of the path.
_EXCLUDED_URLS = "health,ready,metrics"
_HTTP_TIMEOUT_SECONDS = 5


def _clamp_ratio(ratio: float) -> float:
    return min(max(ratio, 0.0), 1.0)


def _resolve_http_experiment_id(uri: str, name: str) -> str:
    """Resolve (or create) the MLflow experiment id via the REST API.

    Deliberately does NOT use ``mlflow.set_experiment``: that mutates MLflow's
    global active experiment/destination and would hijack the agent tracing
    pipeline, sending ``agent.answer`` traces into the HTTP experiment. The HTTP
    pipeline only needs the id for the OTLP ``x-mlflow-experiment-id`` header, so
    we look it up without touching MLflow's global state.
    """
    base = uri.rstrip("/")
    query = urllib.parse.urlencode({"experiment_name": name})
    try:
        with urllib.request.urlopen(
            f"{base}/api/2.0/mlflow/experiments/get-by-name?{query}",
            timeout=_HTTP_TIMEOUT_SECONDS,
        ) as response:
            return str(json.load(response)["experiment"]["experiment_id"])
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise

    create = urllib.request.Request(
        f"{base}/api/2.0/mlflow/experiments/create",
        data=json.dumps({"name": name}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(create, timeout=_HTTP_TIMEOUT_SECONDS) as response:
        return str(json.load(response)["experiment_id"])


def _build_provider(settings: Settings, uri: str):  # type: ignore[no-untyped-def]
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    exp_id = _resolve_http_experiment_id(uri, settings.mlflow_http_experiment)

    provider = TracerProvider(
        resource=Resource.create(
            {"service.name": _SERVICE_NAME, "deployment.environment": settings.app_env}
        ),
        sampler=ParentBased(
            root=TraceIdRatioBased(_clamp_ratio(settings.request_trace_sample_ratio))
        ),
    )
    exporter = OTLPSpanExporter(
        endpoint=f"{uri.rstrip('/')}/v1/traces",
        headers={"x-mlflow-experiment-id": str(exp_id)},
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


def configure_http_tracing(settings: Settings) -> None:
    """Best-effort native-OTel setup for HTTP request tracing. Never raises."""
    global _enabled
    _enabled = False

    if not settings.request_tracing_enabled:
        return

    uri = settings.mlflow_tracking_uri.strip()
    if not uri:
        logger.warning(
            "REQUEST_TRACING_ENABLED is true but MLFLOW_TRACKING_URI is empty; "
            "request tracing disabled."
        )
        return

    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        provider = _build_provider(settings, uri)
        trace.set_tracer_provider(provider)
        HTTPXClientInstrumentor().instrument()
        _enabled = True
        logger.info("HTTP request tracing enabled (otlp=%s/v1/traces).", uri.rstrip("/"))
    except Exception:
        logger.warning("HTTP request tracing setup failed; disabled.", exc_info=True)
        _enabled = False


def instrument_fastapi_app(app: FastAPI) -> None:
    """Attach FastAPI request-span instrumentation when enabled. Never raises."""
    if not _enabled:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        # exclude_spans drops the per-message ASGI "http receive"/"http send"
        # sub-spans, which are noise for our purposes (one root request span with
        # the DB + httpx child spans is what we want).
        FastAPIInstrumentor.instrument_app(
            app, excluded_urls=_EXCLUDED_URLS, exclude_spans=["receive", "send"]
        )
    except Exception:
        logger.warning("FastAPI OTel instrumentation failed.", exc_info=True)


def instrument_sqlalchemy_engine(engine: object) -> None:
    """Attach SQLAlchemy DB-span instrumentation to the async engine. Never raises."""
    if not _enabled:
        return
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        sync_engine = getattr(engine, "sync_engine", engine)
        SQLAlchemyInstrumentor().instrument(engine=sync_engine)
    except Exception:
        logger.warning("SQLAlchemy OTel instrumentation failed.", exc_info=True)


def current_http_trace_id() -> str | None:
    """Hex trace id of the active HTTP request span, or None. Never raises."""
    if not _enabled:
        return None
    try:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if ctx is None or not ctx.is_valid:
            return None
        return format(ctx.trace_id, "032x")
    except Exception:
        logger.debug("current_http_trace_id failed", exc_info=True)
        return None
