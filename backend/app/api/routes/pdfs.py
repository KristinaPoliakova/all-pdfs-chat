from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import get_pdf_upload_service
from app.schemas.pdf import PdfUploadResponse
from app.services.pdf_upload import PdfUploadService

router = APIRouter(prefix="/pdfs", tags=["pdfs"])


@router.post(
    "",
    response_model=PdfUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf(
    file: UploadFile = File(...),
    service: PdfUploadService = Depends(get_pdf_upload_service),
) -> PdfUploadResponse:
    try:
        document = await service.upload(file)
    finally:
        await file.close()
    return PdfUploadResponse.model_validate(document)
