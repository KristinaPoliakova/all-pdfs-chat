from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def format_utc_datetime(value: datetime) -> str:
    utc = ensure_utc(value)
    text = utc.isoformat(timespec="microseconds")
    return text.replace("+00:00", "Z")
