from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.datetime_utils import ensure_utc
from app.db.models.user import User
from app.user_repository.protocol import UserRecord


class SqlUserRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, *, email: str, password_hash: str) -> UserRecord:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
        )
        async with self._session_factory() as session:
            try:
                session.add(user)
                await session.commit()
                await session.refresh(user)
            except Exception:
                await session.rollback()
                raise
        return _to_record(user)

    async def get(self, user_id: str) -> UserRecord:
        async with self._session_factory() as session:
            user = await session.get(User, user_id)
            if user is None:
                raise LookupError(f"User not found: {user_id}")
        return _to_record(user)

    async def get_by_email(self, email: str) -> UserRecord | None:
        normalized = email.strip().lower()
        async with self._session_factory() as session:
            result = await session.execute(select(User).where(User.email == normalized))
            user = result.scalar_one_or_none()
        if user is None:
            return None
        return _to_record(user)

    async def update_password_hash(self, user_id: str, password_hash: str) -> None:
        async with self._session_factory() as session:
            user = await session.get(User, user_id)
            if user is None:
                raise LookupError(f"User not found: {user_id}")
            user.password_hash = password_hash
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise


def _to_record(user: User) -> UserRecord:
    return UserRecord(
        id=user.id,
        email=user.email,
        password_hash=user.password_hash,
        created_at=ensure_utc(user.created_at),
    )
