from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from app.application.auth.exceptions import (
    InvalidCredentialsError,
    InvalidSessionError,
    UserAlreadyExistsError,
)
from app.application.auth.service import AuthService
from app.application.auth.tokens import hash_session_token
from app.infrastructure.persistence.memory.sessions import InMemorySessionRepository
from app.infrastructure.persistence.memory.users import InMemoryUserRepository

from tests.settings_helpers import make_test_settings


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService(
        user_repository=InMemoryUserRepository(),
        session_repository=InMemorySessionRepository(),
        settings=make_test_settings(session_ttl_seconds=3600),
    )


@pytest.mark.asyncio
async def test_register_returns_user_and_token(auth_service: AuthService) -> None:
    result = await auth_service.register(email="alice@example.com", password="secret123")

    assert result.user.email == "alice@example.com"
    assert result.token


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(auth_service: AuthService) -> None:
    await auth_service.register(email="alice@example.com", password="secret123")

    with pytest.raises(UserAlreadyExistsError):
        await auth_service.register(email="alice@example.com", password="other123")


@pytest.mark.asyncio
async def test_login_with_valid_credentials(auth_service: AuthService) -> None:
    await auth_service.register(email="alice@example.com", password="secret123")

    result = await auth_service.login(email="alice@example.com", password="secret123")

    assert result.user.email == "alice@example.com"
    assert result.token


@pytest.mark.asyncio
async def test_login_rejects_invalid_password(auth_service: AuthService) -> None:
    await auth_service.register(email="alice@example.com", password="secret123")

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(email="alice@example.com", password="wrong")


@pytest.mark.asyncio
async def test_logout_revokes_session(auth_service: AuthService) -> None:
    registered = await auth_service.register(email="alice@example.com", password="secret123")

    await auth_service.logout(token=registered.token)

    with pytest.raises(InvalidSessionError):
        await auth_service.get_user_for_token(registered.token)


@pytest.mark.asyncio
async def test_get_user_for_token_rejects_expired_session() -> None:
    users = InMemoryUserRepository()
    sessions = InMemorySessionRepository()
    service = AuthService(
        user_repository=users,
        session_repository=sessions,
        settings=make_test_settings(session_ttl_seconds=3600),
    )
    registered = await service.register(email="alice@example.com", password="secret123")
    session = await sessions.get_by_token_hash(hash_session_token(registered.token))
    assert session is not None
    sessions._records[session.id] = replace(
        session,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    with pytest.raises(InvalidSessionError):
        await service.get_user_for_token(registered.token)
