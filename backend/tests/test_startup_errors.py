from app.db.startup_errors import format_database_startup_error
from sqlalchemy.exc import OperationalError


def test_format_database_startup_error_for_login_timeout() -> None:
    exc = OperationalError(
        "connect",
        {},
        Exception("[HYT00] Login timeout expired"),
    )

    message = format_database_startup_error(exc)

    assert "Azure SQL login timed out" in message
    assert "firewall" in message
    assert "auto-pause" in message
