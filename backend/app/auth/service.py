from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.auth.exceptions import (
    InvalidCredentialsError,
    InvalidSessionError,
    UserAlreadyExistsError,
)
from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import generate_session_token, hash_session_token
from app.config.settings import Settings
from app.session_repository.protocol import SessionRepository
from app.user_repository.protocol import UserRecord, UserRepository


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: UserRecord
    token: str


class AuthService:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        session_repository: SessionRepository,
        settings: Settings,
    ) -> None:
        self._users = user_repository
        self._sessions = session_repository
        self._session_ttl = timedelta(seconds=settings.session_ttl_seconds)

    async def register(self, *, email: str, password: str) -> AuthResult:
        normalized = email.strip().lower()
        if not normalized or not password:
            raise InvalidCredentialsError("Email and password are required")
        existing = await self._users.get_by_email(normalized)
        if existing is not None:
            raise UserAlreadyExistsError(f"User already exists: {normalized}")
        user = await self._users.create(
            email=normalized,
            password_hash=hash_password(password),
        )
        return await self._create_session(user)

    async def login(self, *, email: str, password: str) -> AuthResult:
        normalized = email.strip().lower()
        user = await self._users.get_by_email(normalized)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        return await self._create_session(user)

    async def logout(self, *, token: str) -> None:
        session = await self._sessions.get_by_token_hash(hash_session_token(token))
        if session is None or session.revoked_at is not None:
            return
        await self._sessions.revoke(session.id, revoked_at=datetime.now(UTC))

    async def get_user_for_token(self, token: str) -> UserRecord:
        session = await self._sessions.get_by_token_hash(hash_session_token(token))
        if session is None:
            raise InvalidSessionError("Invalid session token")
        if session.revoked_at is not None:
            raise InvalidSessionError("Session has been revoked")
        now = datetime.now(UTC)
        if session.expires_at <= now:
            raise InvalidSessionError("Session has expired")
        return await self._users.get(session.user_id)

    async def _create_session(self, user: UserRecord) -> AuthResult:
        token = generate_session_token()
        await self._sessions.create(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(UTC) + self._session_ttl,
        )
        return AuthResult(user=user, token=token)
