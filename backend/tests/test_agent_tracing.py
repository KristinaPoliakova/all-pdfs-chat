from __future__ import annotations

import app.agent.tracing as tracing_mod
import pytest

from tests.settings_helpers import make_test_settings


class FakeTracingNamespace:
    def __init__(self) -> None:
        self.disabled = False
        self.enabled = False

    def disable(self) -> None:
        self.disabled = True

    def enable(self) -> None:
        self.enabled = True


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

    def set_experiment(self, name: str) -> None:
        if self._fail_on == "set_experiment":
            raise RuntimeError("boom")
        self.experiment = name


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

    tracing_mod.configure_tracing(
        make_test_settings(
            tracing_enabled=True,
            mlflow_tracking_uri="http://localhost:5000",
            mlflow_experiment="exp",
        )
    )

    assert fake.uri == "http://localhost:5000"
    assert fake.experiment == "exp"
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
