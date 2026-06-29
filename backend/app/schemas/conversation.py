from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.application.ports.conversation import ConversationRecord
from app.application.ports.conversation_memory import ChatMessage
from app.schemas.datetime import UtcDateTime


class ConversationResponse(BaseModel):
    id: str
    pdf_id: str
    title: str | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class RenameConversationRequest(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class MessageResponse(BaseModel):
    role: str
    content: str
    citations: list[int] = Field(default_factory=list)


class ConversationMessagesResponse(BaseModel):
    messages: list[MessageResponse]


def conversation_response_from_record(record: ConversationRecord) -> ConversationResponse:
    return ConversationResponse(
        id=record.id,
        pdf_id=record.pdf_document_id,
        title=record.title,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def message_response_from_chat_message(message: ChatMessage) -> MessageResponse:
    return MessageResponse(
        role=message.role, content=message.content, citations=list(message.citations)
    )
