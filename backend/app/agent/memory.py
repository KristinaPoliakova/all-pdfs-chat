from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.application.ports.conversation_memory import ChatMessage

_PAGE_MARKER = re.compile(r"\[page (\d+)\]")


class LangGraphConversationMemory:
    """Reads/deletes conversation history from the LangGraph checkpointer.

    The only component that understands LangGraph checkpoint internals; keeps the
    application layer free of LangGraph imports.
    """

    def __init__(self, checkpointer: BaseCheckpointSaver[Any]) -> None:
        self._checkpointer = checkpointer

    async def get_messages(self, thread_id: str) -> list[ChatMessage]:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        snapshot = await self._checkpointer.aget_tuple(config)
        if snapshot is None:
            return []
        values = snapshot.checkpoint.get("channel_values", {})
        raw_messages = values.get("messages", []) or []
        return [m for m in (_map_message(raw) for raw in raw_messages) if m is not None]

    async def delete_thread(self, thread_id: str) -> None:
        await self._checkpointer.adelete_thread(thread_id)


def _map_message(message: Any) -> ChatMessage | None:
    if isinstance(message, HumanMessage):
        text = _text(message.content)
        return ChatMessage(role="user", content=text, citations=[]) if text else None
    if isinstance(message, AIMessage):
        if getattr(message, "tool_calls", None):
            return None
        text = _text(message.content)
        if not text:
            return None
        citations = sorted({int(n) for n in _PAGE_MARKER.findall(text)})
        return ChatMessage(role="assistant", content=text, citations=citations)
    return None


def _text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                value = part.get("text", "")
                if isinstance(value, str):
                    parts.append(value)
        return " ".join(parts)
    return str(content)
