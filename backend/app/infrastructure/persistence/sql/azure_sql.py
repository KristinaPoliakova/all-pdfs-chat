from __future__ import annotations

from urllib.parse import quote_plus

DEFAULT_ODBC_DRIVER = "ODBC Driver 18 for SQL Server"
DEFAULT_LOGIN_TIMEOUT_SECONDS = 60

# pyodbc ignores "User ID" / "Password"; ODBC expects UID / PWD.
_ODBC_KEY_ALIASES = {
    "user id": "UID",
    "uid": "UID",
    "password": "PWD",
    "pwd": "PWD",
}


def _normalize_odbc_connection_string(connection_string: str) -> str:
    parts: list[str] = []
    for segment in connection_string.split(";"):
        piece = segment.strip()
        if not piece:
            continue
        if "=" not in piece:
            parts.append(piece)
            continue
        key, value = piece.split("=", 1)
        normalized_key = _ODBC_KEY_ALIASES.get(key.strip().lower(), key.strip())
        parts.append(f"{normalized_key}={value}")
    return ";".join(parts)


def _odbc_has_key(connection_string: str, key: str) -> bool:
    target = key.replace(" ", "").lower()
    for segment in connection_string.split(";"):
        piece = segment.strip()
        if not piece or "=" not in piece:
            continue
        current_key, _ = piece.split("=", 1)
        if current_key.strip().replace(" ", "").lower() == target:
            return True
    return False


def _ensure_odbc_defaults(connection_string: str) -> str:
    """Apply Azure-friendly ODBC defaults when the portal connection string omits them."""
    odbc = connection_string
    defaults: list[tuple[str, str]] = [
        ("LoginTimeout", str(DEFAULT_LOGIN_TIMEOUT_SECONDS)),
        ("Connection Timeout", str(DEFAULT_LOGIN_TIMEOUT_SECONDS)),
    ]
    if "database.windows.net" in odbc.lower() and not _odbc_has_key(odbc, "HostNameInCertificate"):
        defaults.append(("HostNameInCertificate", "*.database.windows.net"))

    for key, value in defaults:
        if not _odbc_has_key(odbc, key):
            odbc = f"{odbc};{key}={value}"
    return odbc


def azure_sql_connectionstring_to_database_url(connection_string: str) -> str:
    """Convert an Azure SQL ODBC/ADO.NET connection string to a SQLAlchemy async URL."""
    value = connection_string.strip()
    if not value:
        msg = "connection_string must not be empty"
        raise ValueError(msg)
    if value.startswith("mssql+"):
        return value

    odbc = _normalize_odbc_connection_string(value)
    if "DRIVER=" not in odbc.upper():
        odbc = f"Driver={{{DEFAULT_ODBC_DRIVER}}};{odbc}"
    odbc = _ensure_odbc_defaults(odbc)
    return f"mssql+aioodbc:///?odbc_connect={quote_plus(odbc)}"


def resolve_prod_database_url(*, azure_sql_connectionstring: str) -> str:
    conn = azure_sql_connectionstring.strip()
    if conn:
        return azure_sql_connectionstring_to_database_url(conn)
    msg = "AZURE_SQL_CONNECTIONSTRING is required when APP_ENV=prod"
    raise ValueError(msg)
