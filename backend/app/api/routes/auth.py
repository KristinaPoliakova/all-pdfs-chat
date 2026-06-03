from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.auth.deps import get_auth_service, get_current_user
from app.application.auth.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.application.auth.service import AuthResult, AuthService
from app.application.ports.users import UserRecord
from app.config import settings as app_settings
from app.core.rate_limit import get_client_ip, limiter
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


def _to_user_response(user: UserRecord) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, created_at=user.created_at)


def _to_auth_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(user=_to_user_response(result.user), token=result.token)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(lambda: app_settings.get_settings().rate_limit_auth_register, key_func=get_client_ip)
async def register(
    request: Request,
    body: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        result = await auth_service.register(email=body.email, password=body.password)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_auth_response(result)


@router.post("/login", response_model=AuthResponse)
@limiter.limit(lambda: app_settings.get_settings().rate_limit_auth_login, key_func=get_client_ip)
async def login(
    request: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        result = await auth_service.login(email=body.email, password=body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return _to_auth_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(lambda: app_settings.get_settings().rate_limit_auth_logout, key_func=get_client_ip)
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    if credentials is not None and credentials.scheme.lower() == "bearer":
        await auth_service.logout(token=credentials.credentials)


@router.get("/me", response_model=UserResponse)
@limiter.limit(lambda: app_settings.get_settings().rate_limit_auth_me, key_func=get_client_ip)
async def me(
    request: Request,
    current_user: UserRecord = Depends(get_current_user),
) -> UserResponse:
    return _to_user_response(current_user)
