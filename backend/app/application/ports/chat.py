from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ChatAnswer:
    answer: str
    citations: list[int]
    recorded: bool = True


class ChatService(Protocol):
    async def answer(
        self, *, conversation_id: str, pdf_id: str, user_id: str, message: str
    ) -> ChatAnswer: ...
