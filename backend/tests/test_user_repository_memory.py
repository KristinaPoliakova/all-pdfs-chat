import pytest
from app.user_repository.memory import InMemoryUserRepository


@pytest.mark.asyncio
async def test_create_user_returns_record() -> None:
    repo = InMemoryUserRepository()

    record = await repo.create(email="alice@example.com", password_hash="hashed")

    assert record.email == "alice@example.com"
    assert record.password_hash == "hashed"
    assert await repo.get(record.id) == record


@pytest.mark.asyncio
async def test_get_by_email_returns_user() -> None:
    repo = InMemoryUserRepository()
    created = await repo.create(email="Bob@Example.com", password_hash="hash")

    found = await repo.get_by_email("bob@example.com")

    assert found == created


@pytest.mark.asyncio
async def test_get_by_email_returns_none_when_missing() -> None:
    repo = InMemoryUserRepository()

    assert await repo.get_by_email("missing@example.com") is None


@pytest.mark.asyncio
async def test_update_password_hash() -> None:
    repo = InMemoryUserRepository()
    created = await repo.create(email="alice@example.com", password_hash="old")

    await repo.update_password_hash(created.id, "new")

    updated = await repo.get(created.id)
    assert updated.password_hash == "new"
