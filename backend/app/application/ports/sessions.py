from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SessionRecord:
    id: str
    user_id: str
    token_hash: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None


class SessionRepository(Protocol):
    async def create(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> SessionRecord: ...

    async def get_by_token_hash(self, token_hash: str) -> SessionRecord | None: ...

    async def revoke(self, session_id: str, *, revoked_at: datetime) -> None: ...

    async def revoke_all_for_user(self, user_id: str, *, revoked_at: datetime) -> None: ...
