from datetime import UTC, datetime, timedelta

import pytest
from app.session_repository.memory import InMemorySessionRepository


@pytest.mark.asyncio
async def test_create_and_get_by_token_hash() -> None:
    repo = InMemorySessionRepository()
    expires_at = datetime.now(UTC) + timedelta(days=1)

    created = await repo.create(
        user_id="user-1",
        token_hash="abc123",
        expires_at=expires_at,
    )

    found = await repo.get_by_token_hash("abc123")

    assert found == created


@pytest.mark.asyncio
async def test_revoke_marks_session() -> None:
    repo = InMemorySessionRepository()
    expires_at = datetime.now(UTC) + timedelta(days=1)
    created = await repo.create(
        user_id="user-1",
        token_hash="abc123",
        expires_at=expires_at,
    )
    revoked_at = datetime.now(UTC)

    await repo.revoke(created.id, revoked_at=revoked_at)

    updated = await repo.get_by_token_hash("abc123")
    assert updated is not None
    assert updated.revoked_at == revoked_at


@pytest.mark.asyncio
async def test_revoke_all_for_user() -> None:
    repo = InMemorySessionRepository()
    expires_at = datetime.now(UTC) + timedelta(days=1)
    first = await repo.create(user_id="user-1", token_hash="t1", expires_at=expires_at)
    second = await repo.create(user_id="user-1", token_hash="t2", expires_at=expires_at)
    other = await repo.create(user_id="user-2", token_hash="t3", expires_at=expires_at)
    revoked_at = datetime.now(UTC)

    await repo.revoke_all_for_user("user-1", revoked_at=revoked_at)

    assert (await repo.get_by_token_hash("t1")).revoked_at == revoked_at
    assert (await repo.get_by_token_hash("t2")).revoked_at == revoked_at
    assert (await repo.get_by_token_hash("t3")).revoked_at is None
    assert first.id != second.id
    assert other.user_id == "user-2"
