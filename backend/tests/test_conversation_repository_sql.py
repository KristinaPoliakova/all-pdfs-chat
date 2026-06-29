from __future__ import annotations

import pytest
from app.infrastructure.persistence.sql.repositories.conversation import SqlConversationRepository
from app.infrastructure.persistence.sql.repositories.pdf import SqlPdfRepository

from tests.db_helpers import open_test_database, seed_sql_user_and_pdf


@pytest.mark.asyncio
async def test_sql_create_get_list_rename_touch_delete() -> None:
    runtime = await open_test_database()
    user_id, pdf_id = await seed_sql_user_and_pdf(runtime, email="conv-sql@example.com")
    repo = SqlConversationRepository(runtime.session_factory)

    created = await repo.create(user_id=user_id, pdf_document_id=pdf_id)
    assert created.title is None

    fetched = await repo.get_for_user(created.id, user_id)
    assert fetched.id == created.id

    with pytest.raises(LookupError):
        await repo.get_for_user(created.id, "other-user")

    await repo.touch(created.id, title_if_unset="auto title")
    await repo.touch(created.id, title_if_unset="ignored second time")
    assert (await repo.get_for_user(created.id, user_id)).title == "auto title"

    await repo.rename(created.id, title="Manual")
    assert (await repo.get_for_user(created.id, user_id)).title == "Manual"

    listed = await repo.list_for_pdf(pdf_id, user_id)
    assert [c.id for c in listed] == [created.id]

    await repo.delete(created.id)
    with pytest.raises(LookupError):
        await repo.get_for_user(created.id, user_id)


@pytest.mark.asyncio
async def test_sql_list_for_pdf_orders_newest_first() -> None:
    runtime = await open_test_database()
    user_id, pdf_id = await seed_sql_user_and_pdf(runtime, email="conv-order@example.com")
    repo = SqlConversationRepository(runtime.session_factory)

    first = await repo.create(user_id=user_id, pdf_document_id=pdf_id)
    second = await repo.create(user_id=user_id, pdf_document_id=pdf_id)
    await repo.touch(first.id, title_if_unset="now newest")

    listed = await repo.list_for_pdf(pdf_id, user_id)
    assert [c.id for c in listed] == [first.id, second.id]


@pytest.mark.asyncio
async def test_deleting_pdf_cascades_conversations() -> None:
    runtime = await open_test_database()
    user_id, pdf_id = await seed_sql_user_and_pdf(runtime, email="conv-cascade@example.com")
    convs = SqlConversationRepository(runtime.session_factory)
    pdfs = SqlPdfRepository(runtime.session_factory)
    conv = await convs.create(user_id=user_id, pdf_document_id=pdf_id)

    await pdfs.delete(pdf_id)

    with pytest.raises(LookupError):
        await convs.get_for_user(conv.id, user_id)
