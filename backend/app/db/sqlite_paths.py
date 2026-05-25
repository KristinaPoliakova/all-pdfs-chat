from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote


def resolve_sqlite_database_url(database_url: str, *, base_dir: Path) -> str:
    """Turn relative sqlite file URLs into absolute paths under base_dir."""
    if "sqlite" not in database_url or "///" not in database_url:
        return database_url

    prefix, remainder = database_url.split("///", 1)
    path_part, _, query = remainder.partition("?")
    raw_path = unquote(path_part)
    if not raw_path or raw_path == ":memory:":
        return database_url
    if Path(raw_path).is_absolute():
        resolved = Path(raw_path)
    else:
        normalized = raw_path.removeprefix("./")
        resolved = (base_dir / normalized).resolve()

    resolved.parent.mkdir(parents=True, exist_ok=True)
    rebuilt = f"{prefix}///{resolved.as_posix()}"
    if query:
        rebuilt = f"{rebuilt}?{query}"
    return rebuilt


def sqlite_file_path(database_url: str) -> Path | None:
    if "sqlite" not in database_url or "///" not in database_url:
        return None

    raw_path = unquote(database_url.split("///", 1)[1].split("?", 1)[0])
    if not raw_path or raw_path == ":memory:":
        return None
    return Path(raw_path)


def ensure_sqlite_parent_dir(database_url: str) -> None:
    db_path = sqlite_file_path(database_url)
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
