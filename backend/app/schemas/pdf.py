from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.classification.types import PageClass, PageClassificationResult, PdfProcessingStatus
from app.metadata.protocol import PdfMetadataRecord


class PdfPageSummary(BaseModel):
    page_number: int = Field(ge=1)
    page_class: PageClass
    confidence: float = Field(ge=0.0, le=1.0)


class PdfDocumentResponse(BaseModel):
    """Document metadata without per-page classification (GET /pdfs/{id})."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    size_bytes: int = Field(gt=0)
    created_at: datetime
    processing_status: PdfProcessingStatus
    page_count: int | None = None
    classification_error: str | None = None
    classified_at: datetime | None = None


class PdfUploadResponse(PdfDocumentResponse):
    """Upload response — includes inline pages for convenience after sync classification."""

    pages: list[PdfPageSummary] = Field(default_factory=list)


class PdfPagesResponse(BaseModel):
    pages: list[PdfPageSummary]


def document_response_from_record(record: PdfMetadataRecord) -> PdfDocumentResponse:
    return PdfDocumentResponse(
        id=record.id,
        filename=record.filename,
        size_bytes=record.size_bytes,
        created_at=record.created_at,
        processing_status=record.processing_status,
        page_count=record.page_count,
        classification_error=record.classification_error,
        classified_at=record.classified_at,
    )


def page_summaries_from_results(
    pages: list[PageClassificationResult],
) -> list[PdfPageSummary]:
    return [
        PdfPageSummary(
            page_number=page.page_number,
            page_class=page.page_class,
            confidence=page.confidence,
        )
        for page in pages
    ]
