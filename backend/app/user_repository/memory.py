from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime

from app.user_repository.protocol import UserRecord


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._records: dict[str, UserRecord] = {}
        self._by_email: dict[str, str] = {}

    async def create(self, *, email: str, password_hash: str) -> UserRecord:
        normalized = email.strip().lower()
        if normalized in self._by_email:
            raise ValueError(f"User already exists: {normalized}")
        record = UserRecord(
            id=str(uuid.uuid4()),
            email=normalized,
            password_hash=password_hash,
            created_at=datetime.now(UTC),
        )
        self._records[record.id] = record
        self._by_email[normalized] = record.id
        return record

    async def get(self, user_id: str) -> UserRecord:
        record = self._records.get(user_id)
        if record is None:
            raise LookupError(f"User not found: {user_id}")
        return record

    async def get_by_email(self, email: str) -> UserRecord | None:
        user_id = self._by_email.get(email.strip().lower())
        if user_id is None:
            return None
        return self._records.get(user_id)

    async def update_password_hash(self, user_id: str, password_hash: str) -> None:
        record = self._records.get(user_id)
        if record is None:
            raise LookupError(f"User not found: {user_id}")
        self._records[user_id] = replace(record, password_hash=password_hash)
