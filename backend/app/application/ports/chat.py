from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ChatAnswer:
    answer: str
    citations: list[int]


class ChatService(Protocol):
    async def answer(self, *, pdf_id: str, user_id: str, message: str) -> ChatAnswer: ...
