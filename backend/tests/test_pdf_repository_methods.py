from __future__ import annotations

import pytest
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository


@pytest.mark.asyncio
async def test_list_for_user_returns_only_my_pdfs_newest_first() -> None:
    repo = InMemoryPdfRepository()
    a = await repo.create(user_id="u1", filename="a.pdf", storage_key="k-a", size_bytes=1)
    b = await repo.create(user_id="u1", filename="b.pdf", storage_key="k-b", size_bytes=1)
    await repo.create(user_id="u2", filename="c.pdf", storage_key="k-c", size_bytes=1)

    listed = await repo.list_for_user("u1")

    assert {r.id for r in listed} == {a.id, b.id}
    assert listed[0].created_at >= listed[-1].created_at


@pytest.mark.asyncio
async def test_rename_changes_filename() -> None:
    repo = InMemoryPdfRepository()
    created = await repo.create(user_id="u1", filename="old.pdf", storage_key="k", size_bytes=1)

    renamed = await repo.rename(created.id, filename="new.pdf")

    assert renamed.filename == "new.pdf"
    assert (await repo.get(created.id)).filename == "new.pdf"


@pytest.mark.asyncio
async def test_delete_removes_pdf() -> None:
    repo = InMemoryPdfRepository()
    created = await repo.create(user_id="u1", filename="x.pdf", storage_key="k", size_bytes=1)

    await repo.delete(created.id)

    with pytest.raises(LookupError):
        await repo.get(created.id)
