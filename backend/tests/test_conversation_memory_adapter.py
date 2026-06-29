from __future__ import annotations

from typing import Any

import pytest
from app.agent.memory import LangGraphConversationMemory
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


class _FakeCheckpointer:
    def __init__(self, tuple_: Any) -> None:
        self._tuple = tuple_
        self.deleted: list[str] = []

    async def aget_tuple(self, config: dict[str, Any]) -> Any:
        return self._tuple

    async def adelete_thread(self, thread_id: str) -> None:
        self.deleted.append(thread_id)


class _Tuple:
    def __init__(self, messages: list[Any]) -> None:
        self.checkpoint = {"channel_values": {"messages": messages}}


@pytest.mark.asyncio
async def test_get_messages_returns_empty_when_no_checkpoint() -> None:
    memory = LangGraphConversationMemory(_FakeCheckpointer(None))

    assert await memory.get_messages("t1") == []


@pytest.mark.asyncio
async def test_get_messages_maps_and_filters() -> None:
    messages = [
        HumanMessage(content="what is on page 2?"),
        AIMessage(content="", tool_calls=[{"name": "search", "args": {}, "id": "1"}]),
        ToolMessage(content="[page 2] some text", tool_call_id="1"),
        AIMessage(content="It says X. [page 2]"),
    ]
    memory = LangGraphConversationMemory(_FakeCheckpointer(_Tuple(messages)))

    result = await memory.get_messages("t1")

    assert [(m.role, m.content) for m in result] == [
        ("user", "what is on page 2?"),
        ("assistant", "It says X. [page 2]"),
    ]
    assert result[1].citations == [2]


@pytest.mark.asyncio
async def test_delete_thread_delegates() -> None:
    checkpointer = _FakeCheckpointer(None)
    memory = LangGraphConversationMemory(checkpointer)

    await memory.delete_thread("t9")

    assert checkpointer.deleted == ["t9"]
