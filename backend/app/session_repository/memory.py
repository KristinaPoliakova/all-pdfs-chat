from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime

from app.session_repository.protocol import SessionRecord


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}
        self._by_token_hash: dict[str, str] = {}

    async def create(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> SessionRecord:
        record = SessionRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
            revoked_at=None,
        )
        self._records[record.id] = record
        self._by_token_hash[token_hash] = record.id
        return record

    async def get_by_token_hash(self, token_hash: str) -> SessionRecord | None:
        session_id = self._by_token_hash.get(token_hash)
        if session_id is None:
            return None
        return self._records.get(session_id)

    async def revoke(self, session_id: str, *, revoked_at: datetime) -> None:
        record = self._records.get(session_id)
        if record is None:
            raise LookupError(f"Session not found: {session_id}")
        self._records[session_id] = replace(record, revoked_at=revoked_at)

    async def revoke_all_for_user(self, user_id: str, *, revoked_at: datetime) -> None:
        for session_id, record in list(self._records.items()):
            if record.user_id == user_id and record.revoked_at is None:
                self._records[session_id] = replace(record, revoked_at=revoked_at)
