from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.auth.exceptions import AuthError
from app.application.auth.service import AuthService
from app.application.ports.sessions import SessionRepository
from app.application.ports.users import UserRecord, UserRepository
from app.config.settings import Settings, get_settings
from app.infrastructure.factories.sessions import create_session_repository
from app.infrastructure.factories.users import create_user_repository

_bearer = HTTPBearer(auto_error=False)


def get_user_repository() -> UserRepository:
    return create_user_repository()


def get_session_repository() -> SessionRepository:
    return create_session_repository()


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    session_repository: SessionRepository = Depends(get_session_repository),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        user_repository=user_repository,
        session_repository=session_repository,
        settings=settings,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserRecord:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return await auth_service.get_user_for_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
