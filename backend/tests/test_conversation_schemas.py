from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.application.ports.conversation import ConversationRecord
from app.schemas.conversation import (
    RenameConversationRequest,
    conversation_response_from_record,
)
from pydantic import ValidationError


def test_conversation_response_maps_pdf_document_id_to_pdf_id() -> None:
    now = datetime.now(UTC)
    record = ConversationRecord(
        id="c1", user_id="u1", pdf_document_id="p1", title=None, created_at=now, updated_at=now
    )

    response = conversation_response_from_record(record)

    assert response.id == "c1"
    assert response.pdf_id == "p1"
    assert response.title is None


def test_rename_request_strips_and_rejects_empty() -> None:
    assert RenameConversationRequest(title="  Hello  ").title == "Hello"
    with pytest.raises(ValidationError):
        RenameConversationRequest(title="   ")
