from fastapi import APIRouter

from app.api.routes import pdfs

api_router = APIRouter()
api_router.include_router(pdfs.router)
