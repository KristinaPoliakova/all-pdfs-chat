from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.application.auth.exceptions import AuthError
from app.application.auth.service import AuthService
from app.config import settings as app_settings
from app.infrastructure.factories.sessions import create_session_repository
from app.infrastructure.factories.users import create_user_repository

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def get_user_id_or_ip(request: Request) -> str:
    user_id = getattr(request.state, "rate_limit_user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_client_ip(request)}"


limiter = Limiter(key_func=get_client_ip, auto_check=True)


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization[7:].strip()
    return token or None


class RateLimitUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request.state.rate_limit_user_id = None
        request.state.view_rate_limit = None
        token = _bearer_token(request)
        if token is not None:
            settings = app_settings.get_settings()
            auth_service = AuthService(
                user_repository=create_user_repository(),
                session_repository=create_session_repository(),
                settings=settings,
            )
            try:
                user = await auth_service.get_user_for_token(token)
            except AuthError:
                pass
            else:
                request.state.rate_limit_user_id = user.id
        return await call_next(request)


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RateLimitExceeded):
        raise exc
    response = JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
    )
    retry_after = _retry_after_seconds(request)
    if retry_after is not None:
        response.headers["Retry-After"] = str(retry_after)
    return response


def _retry_after_seconds(request: Request) -> int | None:
    view_rate_limit = getattr(request.state, "view_rate_limit", None)
    if view_rate_limit is None:
        return None
    app_limiter = getattr(request.app.state, "limiter", None)
    if app_limiter is None:
        return None
    try:
        window_stats = app_limiter.limiter.get_window_stats(
            view_rate_limit[0],
            *view_rate_limit[1],
        )
        reset_at = 1 + window_stats[0]
        return max(1, int(reset_at - time.time()))
    except Exception:
        logger.exception("Failed to compute Retry-After for rate limit response")
        return None


def configure_rate_limiting(app: FastAPI) -> None:
    settings = app_settings.get_settings()
    limiter.enabled = settings.rate_limits_active
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(RateLimitUserMiddleware)
