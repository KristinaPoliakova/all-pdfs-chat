from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.sessions import SessionRecord
from app.core.datetime_utils import ensure_utc
from app.infrastructure.persistence.sql.models.user_session import UserSession


class SqlSessionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> SessionRecord:
        session_row = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        async with self._session_factory() as session:
            try:
                session.add(session_row)
                await session.commit()
                await session.refresh(session_row)
            except Exception:
                await session.rollback()
                raise
        return _to_record(session_row)

    async def get_by_token_hash(self, token_hash: str) -> SessionRecord | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserSession).where(UserSession.token_hash == token_hash),
            )
            row = result.scalar_one_or_none()
        if row is None:
            return None
        return _to_record(row)

    async def revoke(self, session_id: str, *, revoked_at: datetime) -> None:
        async with self._session_factory() as session:
            row = await session.get(UserSession, session_id)
            if row is None:
                raise LookupError(f"Session not found: {session_id}")
            row.revoked_at = revoked_at
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def revoke_all_for_user(self, user_id: str, *, revoked_at: datetime) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(UserSession)
                .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
                .values(revoked_at=revoked_at),
            )
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise


def _to_record(row: UserSession) -> SessionRecord:
    return SessionRecord(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        expires_at=ensure_utc(row.expires_at),
        created_at=ensure_utc(row.created_at),
        revoked_at=ensure_utc(row.revoked_at) if row.revoked_at is not None else None,
    )
