from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str
    citations: list[int]


class ConversationMemoryPort(Protocol):
    async def get_messages(self, thread_id: str) -> list[ChatMessage]: ...

    async def delete_thread(self, thread_id: str) -> None: ...
