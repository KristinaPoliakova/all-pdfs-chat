from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PdfMetadataRecord:
    id: str
    filename: str
    storage_key: str
    size_bytes: int
    created_at: datetime


class PdfMetadataStore(Protocol):
    async def init(self) -> None:
        """Create schema / prepare storage (no-op for in-memory)."""
        ...

    async def close(self) -> None:
        """Release connections (no-op for in-memory)."""
        ...

    async def create(
        self,
        *,
        filename: str,
        storage_key: str,
        size_bytes: int,
    ) -> PdfMetadataRecord: ...
