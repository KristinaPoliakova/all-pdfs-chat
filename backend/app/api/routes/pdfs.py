from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status

from app.api.deps import get_pdf_repository, get_pdf_upload_service
from app.application.auth.deps import get_current_user
from app.application.ports.pdf import PdfRepository
from app.application.ports.users import UserRecord
from app.application.services.pdf_upload import PdfUploadService
from app.config import settings as app_settings
from app.core.rate_limit import get_user_id_or_ip, limiter
from app.schemas.pdf import (
    PdfDocumentResponse,
    PdfPagesResponse,
    document_response_from_record,
    page_summaries_from_results,
)

router = APIRouter(prefix="/pdfs", tags=["pdfs"])


def _pdf_location(pdf_id: str) -> str:
    return f"/api/v1/pdfs/{pdf_id}"


@router.post(
    "",
    response_model=PdfDocumentResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(
    lambda: app_settings.get_settings().rate_limit_pdf_upload,
    key_func=get_user_id_or_ip,
)
async def upload_pdf(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    current_user: UserRecord = Depends(get_current_user),
    service: PdfUploadService = Depends(get_pdf_upload_service),
) -> PdfDocumentResponse:
    try:
        result = await service.upload(file, user_id=current_user.id)
    finally:
        await file.close()
    response.headers["Location"] = _pdf_location(result.record.id)
    return document_response_from_record(result.record)


@router.get("/{pdf_id}", response_model=PdfDocumentResponse, response_model_exclude_none=True)
@limiter.limit(lambda: app_settings.get_settings().rate_limit_pdf_read, key_func=get_user_id_or_ip)
async def get_pdf(
    request: Request,
    pdf_id: str,
    current_user: UserRecord = Depends(get_current_user),
    pdf_repository: PdfRepository = Depends(get_pdf_repository),
) -> PdfDocumentResponse:
    try:
        record = await pdf_repository.get_for_user(pdf_id, current_user.id)
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
@limiter.limit(lambda: app_settings.get_settings().rate_limit_pdf_read, key_func=get_user_id_or_ip)
async def get_pdf_pages(
    request: Request,
    pdf_id: str,
    current_user: UserRecord = Depends(get_current_user),
    pdf_repository: PdfRepository = Depends(get_pdf_repository),
) -> PdfPagesResponse:
    try:
        await pdf_repository.get_for_user(pdf_id, current_user.id)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF document not found",
        ) from None
    pages = await pdf_repository.get_pages(pdf_id)
    return PdfPagesResponse(pages=page_summaries_from_results(pages))
