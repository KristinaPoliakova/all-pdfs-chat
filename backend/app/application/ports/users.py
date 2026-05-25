from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: str
    email: str
    password_hash: str
    created_at: datetime


class UserRepository(Protocol):
    async def create(self, *, email: str, password_hash: str) -> UserRecord: ...

    async def get(self, user_id: str) -> UserRecord: ...

    async def get_by_email(self, email: str) -> UserRecord | None: ...

    async def update_password_hash(self, user_id: str, password_hash: str) -> None: ...
