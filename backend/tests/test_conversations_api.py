from __future__ import annotations

import uuid

import pytest
from app.api.deps import get_chat_service
from app.application.ports.chat import ChatAnswer
from app.application.ports.conversation_memory import ChatMessage
from httpx import AsyncClient

from tests.auth_helpers import register_and_get_auth_headers
from tests.pdf_fixtures import make_text_pdf_bytes


class _FakeChatService:
    async def answer(
        self, *, conversation_id: str, pdf_id: str, user_id: str, message: str
    ) -> ChatAnswer:
        return ChatAnswer(answer=f"echo: {message}", citations=[1])


class _EmptyDocChatService:
    async def answer(
        self, *, conversation_id: str, pdf_id: str, user_id: str, message: str
    ) -> ChatAnswer:
        return ChatAnswer(
            answer="No readable text was found in this document.",
            citations=[],
            recorded=False,
        )


async def _upload_and_parse(api_client: AsyncClient, auth_headers, drain) -> str:
    upload = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", make_text_pdf_bytes(pages=2), "application/pdf")},
        headers=auth_headers,
    )
    pdf_id = upload.json()["id"]
    await drain()
    return pdf_id


@pytest.mark.asyncio
async def test_create_conversation_requires_parsed_pdf(
    api_client: AsyncClient, auth_headers, drain_pdf_jobs
) -> None:
    upload = await api_client.post(
        "/api/v1/pdfs",
        files={"file": ("report.pdf", make_text_pdf_bytes(pages=1), "application/pdf")},
        headers=auth_headers,
    )
    pdf_id = upload.json()["id"]  # not drained → not parsed

    resp = await api_client.post(f"/api/v1/pdfs/{pdf_id}/conversations", headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_and_list_conversations(
    api_client: AsyncClient, auth_headers, drain_pdf_jobs
) -> None:
    pdf_id = await _upload_and_parse(api_client, auth_headers, drain_pdf_jobs)

    created = await api_client.post(f"/api/v1/pdfs/{pdf_id}/conversations", headers=auth_headers)
    assert created.status_code == 201
    body = created.json()
    assert body["pdf_id"] == pdf_id
    assert body["title"] is None

    listed = await api_client.get(f"/api/v1/pdfs/{pdf_id}/conversations", headers=auth_headers)
    assert listed.status_code == 200
    assert [c["id"] for c in listed.json()] == [body["id"]]


@pytest.mark.asyncio
async def test_chat_in_conversation_sets_title_and_returns_answer(
    api_client: AsyncClient, auth_headers, drain_pdf_jobs
) -> None:
    api_client._transport.app.dependency_overrides[get_chat_service] = lambda: _FakeChatService()
    pdf_id = await _upload_and_parse(api_client, auth_headers, drain_pdf_jobs)
    conv = (
        await api_client.post(f"/api/v1/pdfs/{pdf_id}/conversations", headers=auth_headers)
    ).json()

    resp = await api_client.post(
        f"/api/v1/conversations/{conv['id']}/chat",
        json={"message": "What is the revenue?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"answer": "echo: What is the revenue?", "citations": [1]}

    meta = (
        await api_client.get(f"/api/v1/conversations/{conv['id']}", headers=auth_headers)
    ).json()
    assert meta["title"] == "What is the revenue?"


@pytest.mark.asyncio
async def test_empty_document_turn_does_not_set_title(
    api_client: AsyncClient, auth_headers, drain_pdf_jobs
) -> None:
    overrides = api_client._transport.app.dependency_overrides
    overrides[get_chat_service] = lambda: _EmptyDocChatService()
    pdf_id = await _upload_and_parse(api_client, auth_headers, drain_pdf_jobs)
    conv = (
        await api_client.post(f"/api/v1/pdfs/{pdf_id}/conversations", headers=auth_headers)
    ).json()

    resp = await api_client.post(
        f"/api/v1/conversations/{conv['id']}/chat",
        json={"message": "anything"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    meta = (
        await api_client.get(f"/api/v1/conversations/{conv['id']}", headers=auth_headers)
    ).json()
    assert meta["title"] is None


@pytest.mark.asyncio
async def test_cannot_access_other_users_conversation(
    api_client: AsyncClient, auth_headers, drain_pdf_jobs
) -> None:
    pdf_id = await _upload_and_parse(api_client, auth_headers, drain_pdf_jobs)
    conv = (
        await api_client.post(f"/api/v1/pdfs/{pdf_id}/conversations", headers=auth_headers)
    ).json()

    other = await register_and_get_auth_headers(api_client, email="intruder@example.com")
    resp = await api_client.get(f"/api/v1/conversations/{conv['id']}", headers=other)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_messages_returns_history_from_memory(
    api_client: AsyncClient, auth_headers, drain_pdf_jobs, conversation_memory
) -> None:
    pdf_id = await _upload_and_parse(api_client, auth_headers, drain_pdf_jobs)
    conv = (
        await api_client.post(f"/api/v1/pdfs/{pdf_id}/conversations", headers=auth_headers)
    ).json()
    conversation_memory.messages_by_thread[conv["id"]] = [
        ChatMessage(role="user", content="hi", citations=[]),
        ChatMessage(role="assistant", content="hello [page 1]", citations=[1]),
    ]

    resp = await api_client.get(
        f"/api/v1/conversations/{conv['id']}/messages", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "messages": [
            {"role": "user", "content": "hi", "citations": []},
            {"role": "assistant", "content": "hello [page 1]", "citations": [1]},
        ]
    }


@pytest.mark.asyncio
async def test_rename_conversation(api_client: AsyncClient, auth_headers, drain_pdf_jobs) -> None:
    pdf_id = await _upload_and_parse(api_client, auth_headers, drain_pdf_jobs)
    conv = (
        await api_client.post(f"/api/v1/pdfs/{pdf_id}/conversations", headers=auth_headers)
    ).json()

    resp = await api_client.patch(
        f"/api/v1/conversations/{conv['id']}", json={"title": "My chat"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "My chat"


@pytest.mark.asyncio
async def test_delete_conversation_clears_memory(
    api_client: AsyncClient, auth_headers, drain_pdf_jobs, conversation_memory
) -> None:
    pdf_id = await _upload_and_parse(api_client, auth_headers, drain_pdf_jobs)
    conv = (
        await api_client.post(f"/api/v1/pdfs/{pdf_id}/conversations", headers=auth_headers)
    ).json()

    resp = await api_client.delete(f"/api/v1/conversations/{conv['id']}", headers=auth_headers)
    assert resp.status_code == 204
    assert conv["id"] in conversation_memory.deleted

    missing = await api_client.get(f"/api/v1/conversations/{conv['id']}", headers=auth_headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_conversation_routes_require_auth(api_client: AsyncClient) -> None:
    resp = await api_client.get(f"/api/v1/conversations/{uuid.uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_unknown_conversation_returns_404(api_client: AsyncClient, auth_headers) -> None:
    api_client._transport.app.dependency_overrides[get_chat_service] = lambda: _FakeChatService()
    resp = await api_client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/chat", json={"message": "hi"}, headers=auth_headers
    )
    assert resp.status_code == 404
