from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar, cast

import mlflow
from mlflow.entities.trace_location import MlflowExperimentLocation

from app.config.settings import Settings
from app.observability import http_tracing

logger = logging.getLogger(__name__)

_AGENT_SPAN_NAME = "agent.answer"
_enabled = False

AsyncFunc = TypeVar("AsyncFunc", bound=Callable[..., Awaitable[Any]])


def _safe_disable() -> None:
    try:
        mlflow.tracing.disable()
    except Exception:
        logger.debug("MLflow tracing.disable() failed", exc_info=True)


def configure_tracing(settings: Settings) -> None:
    """Best-effort, one-time MLflow tracing setup. Never raises."""
    global _enabled
    _enabled = False

    if not settings.tracing_enabled:
        _safe_disable()
        return

    uri = settings.mlflow_tracking_uri.strip()
    if not uri:
        logger.warning(
            "TRACING_ENABLED is true but MLFLOW_TRACKING_URI is empty; tracing disabled."
        )
        _safe_disable()
        return

    try:
        # Set the tracking URI BEFORE enabling: otherwise MLflow probes for a
        # default local file store, importing backends the slim client omits
        # (e.g. sqlparse) and raising on a remote-only setup.
        mlflow.set_tracking_uri(uri)
        exp_id = mlflow.set_experiment(settings.mlflow_experiment).experiment_id
        mlflow.tracing.set_destination(MlflowExperimentLocation(exp_id))
        mlflow.tracing.enable()
    except Exception:
        logger.warning("MLflow tracing setup failed; tracing disabled.", exc_info=True)
        _safe_disable()
        return

    _enabled = True
    logger.info("MLflow tracing enabled (uri=%s).", uri)


class _AgentTraceHandle:
    """Thin wrapper so callers set span data without importing mlflow or risking raises."""

    def __init__(self, span: Any | None) -> None:
        self._span = span

    def set_outputs(self, outputs: dict[str, Any]) -> None:
        if self._span is None:
            return
        try:
            self._span.set_outputs(outputs)
        except Exception:
            logger.debug("MLflow set_outputs failed", exc_info=True)


def _safe_update_trace(*, session_id: str, user: str, tags: dict[str, Any]) -> None:
    try:
        # session_id/user are written to MLflow's reserved metadata keys
        # (mlflow.trace.session / mlflow.trace.user) so the UI groups the turns of
        # one conversation into a session and lets you filter by user. Plain tags
        # do NOT drive that grouping.
        mlflow.update_current_trace(session_id=session_id, user=user, tags=tags)
    except Exception:
        logger.debug("MLflow update_current_trace failed", exc_info=True)


@contextmanager
def agent_trace(
    *, user_id: str, conversation_id: str, pdf_id: str, app_env: str, message: str
) -> Iterator[_AgentTraceHandle]:
    """Root span for one agent run. No-ops when disabled; never raises from tracing."""
    if not _enabled:
        yield _AgentTraceHandle(None)
        return

    try:
        span_cm = mlflow.start_span(name=_AGENT_SPAN_NAME, span_type="AGENT")
    except Exception:
        logger.debug("MLflow start_span failed; continuing untraced", exc_info=True)
        yield _AgentTraceHandle(None)
        return

    with span_cm as span:
        try:
            span.set_inputs({"message": message})
        except Exception:
            logger.debug("MLflow set_inputs failed", exc_info=True)
        tags: dict[str, Any] = {
            "pdf_id": pdf_id,
            "app_env": app_env,
        }
        http_trace_id = http_tracing.current_http_trace_id()
        if http_trace_id is not None:
            tags["http.trace_id"] = http_trace_id
        # session_id == conversation_id: one MLflow session per conversation thread
        # (thread_id == conversation_id), so grouping traces by conversation_id
        # reconstructs the conversation flow. pdf_id is carried as a tag.
        _safe_update_trace(session_id=conversation_id, user=user_id, tags=tags)
        try:
            yield _AgentTraceHandle(span)
        except Exception as exc:
            _safe_update_trace(
                session_id=conversation_id,
                user=user_id,
                tags={**tags, "error_type": type(exc).__name__},
            )
            raise


def trace_node(name: str, span_type: str) -> Callable[[AsyncFunc], AsyncFunc]:
    """Decorate an async coroutine to emit a span when enabled, else call it directly.

    The mlflow.trace wrapper is created lazily on first enabled call and cached, so
    decoration never touches mlflow and a tracing-setup failure degrades to an
    untraced call instead of breaking the caller.
    """

    def decorator(fn: AsyncFunc) -> AsyncFunc:
        traced: Callable[..., Awaitable[Any]] | None = None
        prepared = False

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal traced, prepared
            if not _enabled:
                return await fn(*args, **kwargs)
            if not prepared:
                prepared = True
                try:
                    traced = mlflow.trace(name=name, span_type=span_type)(fn)
                except Exception:
                    logger.debug("MLflow trace setup failed; node untraced", exc_info=True)
                    traced = None
            if traced is None:
                return await fn(*args, **kwargs)
            return await traced(*args, **kwargs)

        return cast(AsyncFunc, wrapper)

    return decorator
