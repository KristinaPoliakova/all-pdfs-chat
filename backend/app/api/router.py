from fastapi import APIRouter

from app.api.routes import auth, conversations, pdfs

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(pdfs.router)
api_router.include_router(conversations.router)
