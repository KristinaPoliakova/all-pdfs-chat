from __future__ import annotations


class AuthError(Exception):
    """Base class for authentication failures."""


class InvalidCredentialsError(AuthError):
    """Email/password pair is invalid."""


class UserAlreadyExistsError(AuthError):
    """Registration attempted for an existing email."""


class InvalidSessionError(AuthError):
    """Session token is missing, expired, or revoked."""
