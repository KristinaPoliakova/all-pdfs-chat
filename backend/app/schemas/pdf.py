from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PdfUploadResponse(BaseModel):
    """Public upload response — internal storage_key is not exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    size_bytes: int = Field(gt=0)
    created_at: datetime
