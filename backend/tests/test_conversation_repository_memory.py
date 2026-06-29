from __future__ import annotations

import pytest
from app.infrastructure.persistence.memory.conversation import InMemoryConversationRepository


@pytest.mark.asyncio
async def test_create_then_get_for_user_returns_record() -> None:
    repo = InMemoryConversationRepository()
    created = await repo.create(user_id="u1", pdf_document_id="p1")

    fetched = await repo.get_for_user(created.id, "u1")

    assert fetched.id == created.id
    assert fetched.pdf_document_id == "p1"
    assert fetched.title is None


@pytest.mark.asyncio
async def test_get_for_user_rejects_other_user_as_lookup_error() -> None:
    repo = InMemoryConversationRepository()
    created = await repo.create(user_id="u1", pdf_document_id="p1")

    with pytest.raises(LookupError):
        await repo.get_for_user(created.id, "someone-else")


@pytest.mark.asyncio
async def test_list_for_pdf_returns_newest_first() -> None:
    repo = InMemoryConversationRepository()
    first = await repo.create(user_id="u1", pdf_document_id="p1")
    second = await repo.create(user_id="u1", pdf_document_id="p1")
    await repo.touch(first.id, title_if_unset="bump first to newest")

    listed = await repo.list_for_pdf("p1", "u1")

    assert [c.id for c in listed] == [first.id, second.id]


@pytest.mark.asyncio
async def test_touch_sets_title_only_when_unset() -> None:
    repo = InMemoryConversationRepository()
    created = await repo.create(user_id="u1", pdf_document_id="p1")

    await repo.touch(created.id, title_if_unset="first title")
    await repo.touch(created.id, title_if_unset="second title")

    assert (await repo.get_for_user(created.id, "u1")).title == "first title"


@pytest.mark.asyncio
async def test_rename_overwrites_title() -> None:
    repo = InMemoryConversationRepository()
    created = await repo.create(user_id="u1", pdf_document_id="p1")

    await repo.rename(created.id, title="Renamed")

    assert (await repo.get_for_user(created.id, "u1")).title == "Renamed"


@pytest.mark.asyncio
async def test_delete_removes_record() -> None:
    repo = InMemoryConversationRepository()
    created = await repo.create(user_id="u1", pdf_document_id="p1")

    await repo.delete(created.id)

    with pytest.raises(LookupError):
        await repo.get_for_user(created.id, "u1")
