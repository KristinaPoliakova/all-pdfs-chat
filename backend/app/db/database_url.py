from __future__ import annotations

from app.config.settings import Settings
from app.db.azure_sql import resolve_prod_database_url


def database_url_for(*, cfg: Settings) -> str:
    if cfg.is_prod:
        return resolve_prod_database_url(
            azure_sql_connectionstring=cfg.azure_sql_connectionstring,
        )
    return cfg.database_url
