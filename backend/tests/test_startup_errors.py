from app.infrastructure.persistence.sql.startup_errors import format_database_startup_error
from sqlalchemy.exc import OperationalError


def test_format_database_startup_error_for_connection_refused() -> None:
    exc = OperationalError(
        "connect",
        {},
        Exception("connection refused"),
    )

    message = format_database_startup_error(exc)

    assert "PostgreSQL connection refused" in message
    assert "docker compose" in message


def test_format_database_startup_error_for_auth_failure() -> None:
    exc = OperationalError(
        "connect",
        {},
        Exception("password authentication failed for user"),
    )

    message = format_database_startup_error(exc)

    assert "authentication failed" in message


def test_format_database_startup_error_for_ssl() -> None:
    exc = OperationalError(
        "connect",
        {},
        Exception("SSL connection is required"),
    )

    message = format_database_startup_error(exc)

    assert "SSL" in message
    assert "sslmode" in message
