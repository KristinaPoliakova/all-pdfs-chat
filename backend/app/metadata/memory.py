from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.metadata.protocol import PdfMetadataRecord


class InMemoryPdfMetadataStore:
    def __init__(self) -> None:
        self._records: dict[str, PdfMetadataRecord] = {}

    async def init(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def create(
        self,
        *,
        filename: str,
        storage_key: str,
        size_bytes: int,
    ) -> PdfMetadataRecord:
        record = PdfMetadataRecord(
            id=str(uuid.uuid4()),
            filename=filename,
            storage_key=storage_key,
            size_bytes=size_bytes,
            created_at=datetime.now(UTC),
        )
        self._records[record.id] = record
        return record

    def get(self, record_id: str) -> PdfMetadataRecord | None:
        """Test helper — not part of the protocol."""
        return self._records.get(record_id)
