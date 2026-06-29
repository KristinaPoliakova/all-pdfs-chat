from __future__ import annotations

from fastapi import Depends

from app.agent.memory import LangGraphConversationMemory
from app.agent.service import LangGraphChatService
from app.application.ports.chat import ChatService
from app.application.ports.conversation import ConversationRepository
from app.application.ports.conversation_memory import ConversationMemoryPort
from app.application.ports.jobs import JobQueue
from app.application.ports.pdf import PdfRepository
from app.application.ports.storage import FileStorage
from app.application.services.conversation import ConversationService
from app.application.services.pdf_management import PdfManagementService
from app.application.services.pdf_upload import PdfUploadService
from app.config.settings import Settings, get_settings
from app.infrastructure.factories.chat_checkpointer import get_chat_checkpointer
from app.infrastructure.factories.chat_model import create_chat_model
from app.infrastructure.factories.conversation import create_conversation_repository
from app.infrastructure.factories.jobs import create_job_queue
from app.infrastructure.factories.pdf import create_pdf_repository
from app.infrastructure.factories.storage import create_file_storage


def get_file_storage() -> FileStorage:
    return create_file_storage()


def get_pdf_repository() -> PdfRepository:
    return create_pdf_repository()


def get_job_queue() -> JobQueue:
    return create_job_queue()


def get_pdf_upload_service(
    pdf_repository: PdfRepository = Depends(get_pdf_repository),
    storage: FileStorage = Depends(get_file_storage),
    settings: Settings = Depends(get_settings),
    job_queue: JobQueue = Depends(get_job_queue),
) -> PdfUploadService:
    return PdfUploadService(
        pdf_repository=pdf_repository,
        storage=storage,
        settings=settings,
        job_queue=job_queue,
    )


def get_chat_service(
    pdf_repository: PdfRepository = Depends(get_pdf_repository),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    return LangGraphChatService(
        repository=pdf_repository,
        model=create_chat_model(settings),
        checkpointer=get_chat_checkpointer(),
        settings=settings,
    )


def get_conversation_repository() -> ConversationRepository:
    return create_conversation_repository()


def get_conversation_memory() -> ConversationMemoryPort:
    return LangGraphConversationMemory(get_chat_checkpointer())


def get_conversation_service(
    repository: ConversationRepository = Depends(get_conversation_repository),
    memory: ConversationMemoryPort = Depends(get_conversation_memory),
    pdf_repository: PdfRepository = Depends(get_pdf_repository),
) -> ConversationService:
    return ConversationService(repository=repository, memory=memory, pdf_repository=pdf_repository)


def get_pdf_management_service(
    pdf_repository: PdfRepository = Depends(get_pdf_repository),
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
    memory: ConversationMemoryPort = Depends(get_conversation_memory),
    storage: FileStorage = Depends(get_file_storage),
) -> PdfManagementService:
    return PdfManagementService(
        pdf_repository=pdf_repository,
        conversation_repository=conversation_repository,
        memory=memory,
        storage=storage,
    )
