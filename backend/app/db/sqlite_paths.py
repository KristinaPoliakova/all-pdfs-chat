from __future__ import annotations

import os
import stat
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


def ensure_sqlite_writable(database_url: str) -> None:
    """Fail fast with a clear message when the SQLite file or directory is not writable."""
    db_path = sqlite_file_path(database_url)
    if db_path is None:
        return

    parent = db_path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    if not os.access(parent, os.W_OK):
        msg = (
            f"SQLite directory is not writable: {parent}. "
            "Fix permissions or set DATABASE_URL to a writable path."
        )
        raise RuntimeError(msg)

    if db_path.exists() and not os.access(db_path, os.W_OK):
        msg = (
            f"SQLite database file is not writable: {db_path}. "
            "Run: chmod u+w <file> or delete the file and restart."
        )
        raise RuntimeError(msg)

    if db_path.exists() and not db_path.is_file():
        msg = f"SQLite database path is not a file: {db_path}"
        raise RuntimeError(msg)

    if db_path.exists():
        mode = db_path.stat().st_mode
        if not (mode & stat.S_IWUSR):
            msg = (
                f"SQLite database file lacks owner write permission: {db_path} "
                f"(mode={oct(mode & 0o777)}). Run: chmod u+w {db_path}"
            )
            raise RuntimeError(msg)
