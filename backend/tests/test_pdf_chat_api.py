from __future__ import annotations

import uuid

import pytest
from app.agent.exceptions import AgentTimeoutError, AgentUnavailableError
from app.api.deps import get_chat_service
from app.application.ports.chat import ChatAnswer
from app.schemas.chat import ChatRequest, ChatResponse
from httpx import AsyncClient
from pydantic import ValidationError

from tests.pdf_fixtures import make_text_pdf_bytes


def test_chat_request_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_response_shape() -> None:
    response = ChatResponse(answer="hi", citations=[1, 2])
    assert response.answer == "hi"
    assert response.citations == [1, 2]


class _FakeChatService:
    async def answer(
        self, *, conversation_id: str, pdf_id: str, user_id: str, message: str
    ) -> ChatAnswer:
        return ChatAnswer(answer=f"echo: {message}", citations=[1])


class _UnavailableChatService:
    async def answer(
        self, *, conversation_id: str, pdf_id: str, user_id: str, message: str
    ) -> ChatAnswer:
        raise AgentUnavailableError("boom")


class _TimeoutChatService:
    async def answer(
        self, *, conversation_id: str, pdf_id: str, user_id: str, message: str
    ) -> ChatAnswer:
        raise AgentTimeoutError("slow")


async def _conversation(api_client: AsyncClient, auth_headers, drain) -> str:
    upload = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", make_text_pdf_bytes(pages=2), "application/pdf")},
        headers=auth_headers,
    )
    pdf_id = upload.json()["id"]
    await drain()
    conv = await api_client.post(f"/api/v1/pdfs/{pdf_id}/conversations", headers=auth_headers)
    return conv.json()["id"]


@pytest.mark.asyncio
async def test_chat_returns_answer(api_client: AsyncClient, auth_headers, drain_pdf_jobs) -> None:
    api_client._transport.app.dependency_overrides[get_chat_service] = lambda: _FakeChatService()
    conv_id = await _conversation(api_client, auth_headers, drain_pdf_jobs)

    response = await api_client.post(
        f"/api/v1/conversations/{conv_id}/chat", json={"message": "hello?"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == {"answer": "echo: hello?", "citations": [1]}


@pytest.mark.asyncio
async def test_chat_rejects_empty_message(
    api_client: AsyncClient, auth_headers, drain_pdf_jobs
) -> None:
    api_client._transport.app.dependency_overrides[get_chat_service] = lambda: _FakeChatService()
    conv_id = await _conversation(api_client, auth_headers, drain_pdf_jobs)

    response = await api_client.post(
        f"/api/v1/conversations/{conv_id}/chat", json={"message": ""}, headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat", json={"message": "hi"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_502_when_agent_unavailable(
    api_client: AsyncClient, auth_headers, drain_pdf_jobs
) -> None:
    api_client._transport.app.dependency_overrides[get_chat_service] = (
        lambda: _UnavailableChatService()
    )
    conv_id = await _conversation(api_client, auth_headers, drain_pdf_jobs)

    response = await api_client.post(
        f"/api/v1/conversations/{conv_id}/chat", json={"message": "hi"}, headers=auth_headers
    )
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_chat_504_on_agent_timeout(
    api_client: AsyncClient, auth_headers, drain_pdf_jobs
) -> None:
    api_client._transport.app.dependency_overrides[get_chat_service] = lambda: _TimeoutChatService()
    conv_id = await _conversation(api_client, auth_headers, drain_pdf_jobs)

    response = await api_client.post(
        f"/api/v1/conversations/{conv_id}/chat", json={"message": "hi"}, headers=auth_headers
    )
    assert response.status_code == 504
