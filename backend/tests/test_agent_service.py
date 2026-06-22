from __future__ import annotations

import pytest
from app.agent.exceptions import AgentTimeoutError, AgentUnavailableError
from app.agent.service import LangGraphChatService, _message_text
from app.application.ports.pdf import PdfRepository
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from tests.agent_helpers import ScriptedChatModel, make_extract
from tests.settings_helpers import make_test_settings


async def _repo_with_pages(pages: list[tuple[int, str]]) -> tuple[InMemoryPdfRepository, str]:
    repo = InMemoryPdfRepository()
    record = await repo.create(user_id="u1", filename="f.pdf", storage_key="k", size_bytes=10)
    await repo.save_page_extracts(record.id, [make_extract(n, t) for n, t in pages])
    return repo, record.id


def _service(
    repo: PdfRepository, model: ScriptedChatModel, **overrides: object
) -> LangGraphChatService:
    return LangGraphChatService(
        repository=repo,
        model=model,
        checkpointer=MemorySaver(),
        settings=make_test_settings(**overrides),
    )


@pytest.mark.asyncio
async def test_answer_runs_tool_loop_and_collects_citations() -> None:
    repo, pdf_id = await _repo_with_pages([(1, "alpha"), (2, "the tax invoice total")])
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "search_pages", "args": {"query": "tax"}, "id": "c1"}],
            ),
            AIMessage(content="The total is on page 2."),
        ]
    )
    service = _service(repo, model)

    result = await service.answer(pdf_id=pdf_id, user_id="u1", message="what is the total?")

    assert "page 2" in result.answer.lower()
    assert result.citations == [2]


@pytest.mark.asyncio
async def test_answer_short_circuits_empty_document() -> None:
    repo = InMemoryPdfRepository()
    record = await repo.create(user_id="u1", filename="f.pdf", storage_key="k", size_bytes=10)
    model = ScriptedChatModel(responses=[])
    service = _service(repo, model)

    result = await service.answer(pdf_id=record.id, user_id="u1", message="hello")

    assert "no readable text" in result.answer.lower()
    assert result.citations == []


@pytest.mark.asyncio
async def test_answer_iteration_guard_terminates() -> None:
    repo, pdf_id = await _repo_with_pages([(1, "alpha")])
    looping = [
        AIMessage(
            content="thinking",
            tool_calls=[{"name": "search_pages", "args": {"query": "x"}, "id": f"c{i}"}],
        )
        for i in range(10)
    ]
    model = ScriptedChatModel(responses=looping)
    service = _service(repo, model, agent_max_tool_iterations=2)

    result = await service.answer(pdf_id=pdf_id, user_id="u1", message="loop?")

    assert result.answer == "thinking"


@pytest.mark.asyncio
async def test_answer_maps_timeout() -> None:
    repo, pdf_id = await _repo_with_pages([(1, "alpha")])
    model = ScriptedChatModel(responses=[AIMessage(content="done")])
    service = _service(repo, model, agent_timeout_seconds=0)

    with pytest.raises(AgentTimeoutError):
        await service.answer(pdf_id=pdf_id, user_id="u1", message="hi")


@pytest.mark.asyncio
async def test_answer_maps_model_error() -> None:
    repo, pdf_id = await _repo_with_pages([(1, "alpha")])
    model = ScriptedChatModel(responses=[])  # IndexError inside the agent node

    service = _service(repo, model)

    with pytest.raises(AgentUnavailableError):
        await service.answer(pdf_id=pdf_id, user_id="u1", message="hi")


@pytest.mark.asyncio
async def test_answer_continues_after_tool_failure() -> None:
    repo, pdf_id = await _repo_with_pages([(1, "alpha")])
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "search_pages", "args": {}, "id": "c1"}],
            ),
            AIMessage(content="final answer"),
        ]
    )
    service = _service(repo, model)

    result = await service.answer(pdf_id=pdf_id, user_id="u1", message="recover?")

    assert result.answer == "final answer"


async def test_answer_succeeds_when_tracing_backend_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.agent.tracing as tracing_mod

    class Boom:
        class tracing:
            @staticmethod
            def disable() -> None:
                return None

        @staticmethod
        def start_span(*args: object, **kwargs: object) -> object:
            raise RuntimeError("mlflow down")

        @staticmethod
        def update_current_trace(**kwargs: object) -> None:
            raise RuntimeError("mlflow down")

    monkeypatch.setattr(tracing_mod, "mlflow", Boom)
    monkeypatch.setattr(tracing_mod, "_enabled", True)

    repo, pdf_id = await _repo_with_pages([(1, "alpha"), (2, "the tax invoice total")])
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "search_pages", "args": {"query": "tax"}, "id": "c1"}],
            ),
            AIMessage(content="The total is on page 2."),
        ]
    )
    service = _service(repo, model)

    result = await service.answer(pdf_id=pdf_id, user_id="u1", message="what is the total?")

    assert result.citations == [2]


def test_message_text_handles_list_content() -> None:
    blocks = [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]

    assert _message_text(blocks) == "hello world"
    assert _message_text("plain string") == "plain string"
