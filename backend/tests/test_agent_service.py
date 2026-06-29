from __future__ import annotations

import pytest
from app.agent.service import _NO_ANSWER_FALLBACK, LangGraphChatService
from app.application.ports.chat import ChatAnswer
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository
from langchain_core.messages import AIMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from tests.agent_helpers import ScriptedChatModel, make_extract
from tests.settings_helpers import make_test_settings


class _NullCheckpointer(BaseCheckpointSaver):
    # langgraph validates the checkpointer type at compile; the empty-document
    # early-return branch never invokes the graph, so no saver methods are called.
    pass


@pytest.mark.asyncio
async def test_answer_returns_empty_document_message_without_extracts() -> None:
    pdfs = InMemoryPdfRepository()
    created = await pdfs.create(user_id="u1", filename="d.pdf", storage_key="k", size_bytes=1)

    class _Model:
        def bind_tools(self, tools):  # noqa: ANN001
            return self

    service = LangGraphChatService(
        repository=pdfs,
        model=_Model(),
        checkpointer=_NullCheckpointer(),
        settings=make_test_settings(),
    )

    answer = await service.answer(
        conversation_id="c1", pdf_id=created.id, user_id="u1", message="hi"
    )

    assert isinstance(answer, ChatAnswer)
    assert answer.citations == []
    assert answer.recorded is False


@pytest.mark.asyncio
async def test_answer_falls_back_when_model_returns_blank_text() -> None:
    pdfs = InMemoryPdfRepository()
    created = await pdfs.create(user_id="u1", filename="d.pdf", storage_key="k", size_bytes=1)
    await pdfs.save_page_extracts(created.id, [make_extract(1, "some readable content")])
    # Model produces a final message with no usable text (no tool calls, empty body).
    model = ScriptedChatModel(responses=[AIMessage(content="   ")])

    service = LangGraphChatService(
        repository=pdfs,
        model=model,
        checkpointer=MemorySaver(),
        settings=make_test_settings(),
    )

    answer = await service.answer(
        conversation_id="c1", pdf_id=created.id, user_id="u1", message="who is mentioned?"
    )

    assert answer.answer == _NO_ANSWER_FALLBACK
    assert answer.citations == []
