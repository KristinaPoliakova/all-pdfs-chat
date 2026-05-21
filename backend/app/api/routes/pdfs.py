from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.api.deps import get_pdf_metadata_store, get_pdf_upload_service
from app.metadata.protocol import PdfMetadataStore
from app.schemas.pdf import (
    PdfDocumentResponse,
    PdfPagesResponse,
    document_response_from_record,
    page_summaries_from_results,
)
from app.services.pdf_upload import PdfUploadService

router = APIRouter(prefix="/pdfs", tags=["pdfs"])


def _pdf_location(pdf_id: str) -> str:
    return f"/api/v1/pdfs/{pdf_id}"


@router.post(
    "",
    response_model=PdfDocumentResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf(
    response: Response,
    file: UploadFile = File(...),
    service: PdfUploadService = Depends(get_pdf_upload_service),
) -> PdfDocumentResponse:
    try:
        result = await service.upload(file)
    finally:
        await file.close()
    response.headers["Location"] = _pdf_location(result.record.id)
    return document_response_from_record(result.record)


@router.get("/{pdf_id}", response_model=PdfDocumentResponse, response_model_exclude_none=True)
async def get_pdf(
    pdf_id: str,
    metadata_store: PdfMetadataStore = Depends(get_pdf_metadata_store),
) -> PdfDocumentResponse:
    try:
        record = await metadata_store.get(pdf_id)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF document not found",
        ) from None
    return document_response_from_record(record)


@router.get(
    "/{pdf_id}/pages",
    response_model=PdfPagesResponse,
    response_model_exclude_none=True,
)
async def get_pdf_pages(
    pdf_id: str,
    metadata_store: PdfMetadataStore = Depends(get_pdf_metadata_store),
) -> PdfPagesResponse:
    try:
        await metadata_store.get(pdf_id)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF document not found",
        ) from None
    pages = await metadata_store.get_pages(pdf_id)
    return PdfPagesResponse(pages=page_summaries_from_results(pages))
