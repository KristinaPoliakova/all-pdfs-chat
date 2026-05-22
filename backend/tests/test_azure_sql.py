from urllib.parse import unquote_plus

import pytest
from app.config.settings import Settings, get_settings
from app.db.azure_sql import (
    azure_sql_connectionstring_to_database_url,
    resolve_prod_database_url,
)
from app.metadata.factory import create_pdf_metadata_store, reset_metadata_store_state


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
async def _reset_metadata_factory() -> None:
    await reset_metadata_store_state()
    yield
    await reset_metadata_store_state()


def test_connectionstring_converts_to_odbc_connect_url() -> None:
    connection_string = (
        "Server=tcp:myserver.database.windows.net,1433;"
        "Initial Catalog=mydb;"
        "User ID=admin;"
        "Password=secret;"
        "Encrypt=yes;"
    )

    url = azure_sql_connectionstring_to_database_url(connection_string)

    assert url.startswith("mssql+aioodbc:///?odbc_connect=")
    odbc = unquote_plus(url.split("odbc_connect=", 1)[1])
    assert "Driver={ODBC Driver 18 for SQL Server};" in odbc
    assert "Server=tcp:myserver.database.windows.net,1433;" in odbc
    assert "Initial Catalog=mydb;" in odbc


def test_connectionstring_normalizes_sql_auth_keys_for_pyodbc() -> None:
    connection_string = (
        "Server=tcp:myserver.database.windows.net,1433;"
        "Database=mydb;"
        "User ID=app_user;"
        "Password=secret;"
        "Encrypt=yes;"
    )

    url = azure_sql_connectionstring_to_database_url(connection_string)
    odbc = unquote_plus(url.split("odbc_connect=", 1)[1])

    assert "UID=app_user" in odbc
    assert "PWD=secret" in odbc
    assert "User ID=" not in odbc
    assert "Password=" not in odbc


def test_connectionstring_passthrough_sqlalchemy_url() -> None:
    sqlalchemy_url = "mssql+aioodbc://user:pass@host/db?driver=ODBC+Driver+18+for+SQL+Server"

    assert azure_sql_connectionstring_to_database_url(sqlalchemy_url) == sqlalchemy_url


def test_resolve_prod_database_url_uses_connectionstring() -> None:
    url = resolve_prod_database_url(
        azure_sql_connectionstring="Server=tcp:host,1433;Initial Catalog=db;User ID=u;Password=p;",
    )

    assert url.startswith("mssql+aioodbc:///?odbc_connect=")


def test_resolve_prod_database_url_requires_connectionstring() -> None:
    with pytest.raises(ValueError, match="AZURE_SQL_CONNECTIONSTRING"):
        resolve_prod_database_url(azure_sql_connectionstring="")


def test_settings_reads_azure_sql_connectionstring_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AZURE_SQL_CONNECTIONSTRING",
        "Server=tcp:host,1433;Initial Catalog=db;User ID=u;Password=p;",
    )

    settings = Settings(_env_file=None)

    assert settings.azure_sql_connectionstring.startswith("Server=tcp:host")


@pytest.mark.asyncio
async def test_factory_uses_connectionstring_for_prod() -> None:
    settings = Settings(
        app_env="prod",
        azure_sql_connectionstring=(
            "Server=tcp:prod.database.windows.net,1433;"
            "Initial Catalog=pdfs;"
            "User ID=app;"
            "Password=secret;"
        ),
        azure_storage_connection_string="blob-conn",
        _env_file=None,
    )

    store = create_pdf_metadata_store(settings)

    assert store._database_url.startswith("mssql+aioodbc:///?odbc_connect=")
