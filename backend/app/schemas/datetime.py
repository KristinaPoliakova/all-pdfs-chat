from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer

from app.core.datetime_utils import format_utc_datetime

UtcDateTime = Annotated[
    datetime,
    PlainSerializer(format_utc_datetime, when_used="json"),
]
