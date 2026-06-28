from __future__ import annotations

import app.agent.tracing as tracing_mod
import app.observability.http_tracing as http_tracing
import pytest

from tests.settings_helpers import make_test_settings


class _FakeExperiment:
    def __init__(self, experiment_id: str) -> None:
        self.experiment_id = experiment_id


class FakeTracingNamespace:
    def __init__(self) -> None:
        self.disabled = False
        self.enabled = False
        self.destination: object | None = None

    def disable(self) -> None:
        self.disabled = True

    def enable(self) -> None:
        self.enabled = True

    def set_destination(self, destination: object) -> None:
        self.destination = destination


class FakeMlflow:
    def __init__(self, fail_on: str | None = None) -> None:
        self.tracing = FakeTracingNamespace()
        self.uri: str | None = None
        self.experiment: str | None = None
        self._fail_on = fail_on

    def set_tracking_uri(self, uri: str) -> None:
        if self._fail_on == "set_tracking_uri":
            raise RuntimeError("boom")
        self.uri = uri

    def set_experiment(self, name: str) -> _FakeExperiment:
        if self._fail_on == "set_experiment":
            raise RuntimeError("boom")
        self.experiment = name
        return _FakeExperiment(experiment_id="exp-id")


@pytest.fixture(autouse=True)
def _reset_tracing_flag() -> None:
    tracing_mod._enabled = False
    yield
    tracing_mod._enabled = False


def test_configure_tracing_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMlflow()
    monkeypatch.setattr(tracing_mod, "mlflow", fake)

    tracing_mod.configure_tracing(make_test_settings(tracing_enabled=False))

    assert fake.tracing.disabled is True
    assert tracing_mod._enabled is False


def test_configure_tracing_enabled_without_uri_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMlflow()
    monkeypatch.setattr(tracing_mod, "mlflow", fake)

    tracing_mod.configure_tracing(make_test_settings(tracing_enabled=True, mlflow_tracking_uri=""))

    assert fake.tracing.disabled is True
    assert tracing_mod._enabled is False


def test_configure_tracing_enabled_sets_uri_and_experiment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeMlflow()
    monkeypatch.setattr(tracing_mod, "mlflow", fake)
    monkeypatch.setattr(tracing_mod, "MlflowExperimentLocation", lambda exp_id: ("loc", exp_id))

    tracing_mod.configure_tracing(
        make_test_settings(
            tracing_enabled=True,
            mlflow_tracking_uri="http://localhost:5000",
            mlflow_experiment="exp",
        )
    )

    assert fake.uri == "http://localhost:5000"
    assert fake.experiment == "exp"
    assert fake.tracing.destination == ("loc", "exp-id")
    assert fake.tracing.enabled is True
    assert tracing_mod._enabled is True


def test_configure_tracing_never_raises_when_disable_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BoomTracing:
        def disable(self) -> None:
            raise RuntimeError("disable boom")

        def enable(self) -> None:
            return None

    class BoomMlflow:
        tracing = BoomTracing()

    monkeypatch.setattr(tracing_mod, "mlflow", BoomMlflow())

    # Default-off startup path calls disable(); it must swallow the failure, not raise.
    tracing_mod.configure_tracing(make_test_settings(tracing_enabled=False))

    assert tracing_mod._enabled is False


def test_configure_tracing_swallows_setup_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMlflow(fail_on="set_experiment")
    monkeypatch.setattr(tracing_mod, "mlflow", fake)

    tracing_mod.configure_tracing(
        make_test_settings(tracing_enabled=True, mlflow_tracking_uri="http://localhost:5000")
    )

    assert fake.tracing.disabled is True
    assert tracing_mod._enabled is False


def test_agent_trace_is_noop_when_disabled() -> None:
    tracing_mod._enabled = False

    with tracing_mod.agent_trace(user_id="u", pdf_id="p", app_env="dev", message="hi") as handle:
        handle.set_outputs({"answer": "x", "citations": []})


def test_agent_trace_swallows_mlflow_errors_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Boom:
        tracing = FakeTracingNamespace()

        def start_span(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError("server down")

        def update_current_trace(self, **kwargs: object) -> None:
            raise RuntimeError("server down")

    monkeypatch.setattr(tracing_mod, "mlflow", Boom())
    tracing_mod._enabled = True

    with tracing_mod.agent_trace(user_id="u", pdf_id="p", app_env="dev", message="hi") as handle:
        handle.set_outputs({"answer": "x", "citations": []})


class _CapturingSpan:
    def set_inputs(self, *a: object, **k: object) -> None: ...
    def set_outputs(self, *a: object, **k: object) -> None: ...


class _CapturingCM:
    def __enter__(self) -> _CapturingSpan:
        return _CapturingSpan()

    def __exit__(self, *a: object) -> bool:
        return False


def _make_capturing_mlflow(calls: list[dict[str, object]]) -> type:
    class FakeMlflowLink:
        class tracing:
            @staticmethod
            def disable() -> None: ...

        @staticmethod
        def start_span(*a: object, **k: object) -> _CapturingCM:
            return _CapturingCM()

        @staticmethod
        def update_current_trace(**k: object) -> None:
            calls.append(k)

    return FakeMlflowLink


def test_agent_trace_groups_turns_by_session_and_user(monkeypatch: pytest.MonkeyPatch) -> None:
    # Conversation grouping in MLflow is driven by the dedicated session_id/user
    # params (reserved metadata keys), NOT by tags. session_id == pdf_id because a
    # chat thread maps 1:1 to a PDF (thread_id == pdf_id).
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(tracing_mod, "mlflow", _make_capturing_mlflow(calls))
    monkeypatch.setattr(tracing_mod, "_enabled", True)
    monkeypatch.setattr(http_tracing, "current_http_trace_id", lambda: None)

    with tracing_mod.agent_trace(user_id="user-1", pdf_id="pdf-9", app_env="dev", message="hi"):
        pass

    assert len(calls) == 1
    call = calls[0]
    assert call.get("session_id") == "pdf-9"
    assert call.get("user") == "user-1"
    tags = call.get("tags", {})
    assert tags == {"pdf_id": "pdf-9", "app_env": "dev"}


def test_agent_trace_tags_http_trace_id_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(tracing_mod, "mlflow", _make_capturing_mlflow(calls))
    monkeypatch.setattr(tracing_mod, "_enabled", True)
    monkeypatch.setattr(http_tracing, "current_http_trace_id", lambda: "abc123")

    with tracing_mod.agent_trace(user_id="u", pdf_id="p", app_env="dev", message="hi"):
        pass

    assert len(calls) == 1
    assert calls[0].get("tags", {}).get("http.trace_id") == "abc123"


def test_agent_trace_records_error_and_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    # On failure the trace must record the error type (alongside session_id/user)
    # and re-raise the ORIGINAL exception — not a TypeError from a bad call.
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(tracing_mod, "mlflow", _make_capturing_mlflow(calls))
    monkeypatch.setattr(tracing_mod, "_enabled", True)
    monkeypatch.setattr(http_tracing, "current_http_trace_id", lambda: None)

    with pytest.raises(ValueError, match="boom"):
        with tracing_mod.agent_trace(user_id="user-1", pdf_id="pdf-9", app_env="dev", message="hi"):
            raise ValueError("boom")

    error_calls = [c for c in calls if "error_type" in c.get("tags", {})]
    assert len(error_calls) == 1
    call = error_calls[0]
    assert call.get("session_id") == "pdf-9"
    assert call.get("user") == "user-1"
    tags = call.get("tags", {})
    assert tags.get("error_type") == "ValueError"
    assert tags.get("pdf_id") == "pdf-9"


async def test_trace_node_runs_fn_directly_when_disabled() -> None:
    tracing_mod._enabled = False
    calls: list[int] = []

    @tracing_mod.trace_node("n", "LLM")
    async def fn(x: int) -> int:
        calls.append(x)
        return x * 2

    result = await fn(3)

    assert result == 6
    assert calls == [3]


async def test_trace_node_falls_back_when_trace_setup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Boom:
        def trace(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError("no trace available")

    monkeypatch.setattr(tracing_mod, "mlflow", Boom())
    tracing_mod._enabled = True

    @tracing_mod.trace_node("n", "TOOL")
    async def fn(x: int) -> int:
        return x + 1

    result = await fn(1)

    assert result == 2
