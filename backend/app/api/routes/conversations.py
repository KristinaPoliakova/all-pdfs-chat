from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.agent.exceptions import AgentTimeoutError, AgentUnavailableError
from app.api.deps import get_chat_service, get_conversation_service
from app.application.auth.deps import get_current_user
from app.application.ports.chat import ChatService
from app.application.ports.users import UserRecord
from app.application.services.conversation import ConversationService, PdfNotReadyError
from app.config import settings as app_settings
from app.core.rate_limit import get_user_id_or_ip, limiter
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.conversation import (
    ConversationMessagesResponse,
    ConversationResponse,
    RenameConversationRequest,
    conversation_response_from_record,
    message_response_from_chat_message,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


@router.get("/{conversation_id}", response_model=ConversationResponse)
@limiter.limit(lambda: app_settings.get_settings().rate_limit_pdf_read, key_func=get_user_id_or_ip)
async def get_conversation(
    request: Request,
    conversation_id: str,
    current_user: UserRecord = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    try:
        record = await service.get(conversation_id=conversation_id, user_id=current_user.id)
    except LookupError:
        raise _not_found() from None
    return conversation_response_from_record(record)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
@limiter.limit(lambda: app_settings.get_settings().rate_limit_pdf_read, key_func=get_user_id_or_ip)
async def rename_conversation(
    request: Request,
    conversation_id: str,
    body: RenameConversationRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    try:
        record = await service.rename(
            conversation_id=conversation_id, user_id=current_user.id, title=body.title
        )
    except LookupError:
        raise _not_found() from None
    return conversation_response_from_record(record)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(lambda: app_settings.get_settings().rate_limit_pdf_read, key_func=get_user_id_or_ip)
async def delete_conversation(
    request: Request,
    conversation_id: str,
    current_user: UserRecord = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> Response:
    try:
        await service.delete(conversation_id=conversation_id, user_id=current_user.id)
    except LookupError:
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/messages", response_model=ConversationMessagesResponse)
@limiter.limit(lambda: app_settings.get_settings().rate_limit_pdf_read, key_func=get_user_id_or_ip)
async def get_conversation_messages(
    request: Request,
    conversation_id: str,
    current_user: UserRecord = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationMessagesResponse:
    try:
        messages = await service.get_messages(
            conversation_id=conversation_id, user_id=current_user.id
        )
    except LookupError:
        raise _not_found() from None
    return ConversationMessagesResponse(
        messages=[message_response_from_chat_message(m) for m in messages]
    )


@router.post("/{conversation_id}/chat", response_model=ChatResponse)
@limiter.limit(lambda: app_settings.get_settings().rate_limit_pdf_read, key_func=get_user_id_or_ip)
async def chat_in_conversation(
    request: Request,
    conversation_id: str,
    body: ChatRequest,
    current_user: UserRecord = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        conversation, _pdf = await conversation_service.get_pdf_for_chat(
            conversation_id=conversation_id, user_id=current_user.id
        )
    except LookupError:
        raise _not_found() from None
    except PdfNotReadyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="PDF is not ready for chat yet"
        ) from None

    try:
        result = await chat_service.answer(
            conversation_id=conversation_id,
            pdf_id=conversation.pdf_document_id,
            user_id=current_user.id,
            message=body.message,
        )
    except AgentTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The assistant took too long to respond. Please try again.",
        ) from None
    except AgentUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assistant is temporarily unavailable. Please try again.",
        ) from None

    if result.recorded:
        await conversation_service.record_turn(
            conversation_id=conversation_id, first_message=body.message
        )
    return ChatResponse(answer=result.answer, citations=result.citations)
