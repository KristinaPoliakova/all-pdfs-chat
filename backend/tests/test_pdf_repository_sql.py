import pytest

from tests.db_helpers import (
    make_sql_pdf_repository,
    make_sql_user_repository,
    open_test_database,
)


@pytest.mark.asyncio
async def test_sql_store_persists_metadata() -> None:
    runtime = await open_test_database()
    users = make_sql_user_repository(runtime)
    store = make_sql_pdf_repository(runtime)
    user = await users.create(email="alice@example.com", password_hash="hash")

    record = await store.create(
        user_id=user.id,
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    assert record.filename == "doc.pdf"
    assert record.storage_key == "pdfs/uuid-doc.pdf"
    assert record.size_bytes == 100
    assert record.user_id == user.id

    await runtime.close()


@pytest.mark.asyncio
async def test_get_for_user_returns_record_for_owner() -> None:
    runtime = await open_test_database()
    users = make_sql_user_repository(runtime)
    store = make_sql_pdf_repository(runtime)
    user = await users.create(email="alice@example.com", password_hash="hash")
    record = await store.create(
        user_id=user.id,
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    owned = await store.get_for_user(record.id, user.id)

    assert owned.id == record.id
    await runtime.close()


@pytest.mark.asyncio
async def test_get_for_user_raises_for_other_owner() -> None:
    runtime = await open_test_database()
    users = make_sql_user_repository(runtime)
    store = make_sql_pdf_repository(runtime)
    owner = await users.create(email="alice@example.com", password_hash="hash")
    other = await users.create(email="bob@example.com", password_hash="hash")
    record = await store.create(
        user_id=owner.id,
        filename="doc.pdf",
        storage_key="pdfs/uuid-doc.pdf",
        size_bytes=100,
    )

    with pytest.raises(LookupError):
        await store.get_for_user(record.id, other.id)
    await runtime.close()
