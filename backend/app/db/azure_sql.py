from __future__ import annotations

from urllib.parse import quote_plus

DEFAULT_ODBC_DRIVER = "ODBC Driver 18 for SQL Server"

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
    return f"mssql+aioodbc:///?odbc_connect={quote_plus(odbc)}"


def resolve_prod_database_url(*, azure_sql_connectionstring: str) -> str:
    conn = azure_sql_connectionstring.strip()
    if conn:
        return azure_sql_connectionstring_to_database_url(conn)
    msg = "AZURE_SQL_CONNECTIONSTRING is required when APP_ENV=prod"
    raise ValueError(msg)
