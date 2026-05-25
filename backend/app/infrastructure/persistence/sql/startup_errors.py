from __future__ import annotations

import logging

from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


def format_database_startup_error(exc: OperationalError) -> str:
    message = str(exc.orig) if exc.orig is not None else str(exc)
    if "HYT00" in message or "Login timeout" in message:
        return (
            "Azure SQL login timed out during startup (APP_ENV=prod). "
            "Common causes: (1) database auto-pause waking up — retry in ~60s, "
            "(2) your public IP is not in the Azure SQL firewall — add it in Azure Portal "
            "→ SQL server → Networking, (3) wrong AZURE_SQL_CONNECTIONSTRING. "
            f"Driver error: {message}"
        )
    return f"Database startup failed: {message}"
