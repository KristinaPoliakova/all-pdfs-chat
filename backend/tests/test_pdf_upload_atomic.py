from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.config.settings import Settings
from app.services.pdf_upload import PdfUploadService
from app.storage.memory import InMemoryFileStorage
from fastapi import UploadFile


def _pdf_upload_file() -> UploadFile:
    return UploadFile(
        file=BytesIO(b"%PDF-1.4\n" + b"0" * 55),
        filename="report.pdf",
        headers={"content-type": "application/pdf"},
    )


@pytest.mark.asyncio
async def test_metadata_not_saved_when_storage_upload_fails() -> None:
    storage = MagicMock()
    storage.upload.side_effect = OSError("disk full")
    metadata = AsyncMock()
    settings = Settings(_env_file=None)

    service = PdfUploadService(
        metadata_store=metadata,
        storage=storage,
        settings=settings,
    )

    with pytest.raises(OSError, match="disk full"):
        await service.upload(_pdf_upload_file())

    metadata.create.assert_not_called()


@pytest.mark.asyncio
async def test_storage_removed_when_metadata_save_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage_key = "pdfs/fixed-key-report.pdf"
    monkeypatch.setattr(
        "app.services.pdf_upload.build_storage_key",
        lambda _filename: storage_key,
    )

    storage = InMemoryFileStorage()
    metadata = AsyncMock()
    metadata.create.side_effect = RuntimeError("db unavailable")
    settings = Settings(_env_file=None)

    service = PdfUploadService(
        metadata_store=metadata,
        storage=storage,
        settings=settings,
    )

    with pytest.raises(RuntimeError, match="db unavailable"):
        await service.upload(_pdf_upload_file())

    assert not storage.exists(storage_key)
