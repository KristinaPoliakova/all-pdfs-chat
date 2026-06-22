from __future__ import annotations

import pytest
from app.agent.exceptions import MissingPdfContextError
from app.agent.tools import make_pdf_tools
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository

from tests.agent_helpers import make_extract


async def _repo_with_pages(pages: list[tuple[int, str]]) -> tuple[InMemoryPdfRepository, str]:
    repo = InMemoryPdfRepository()
    record = await repo.create(user_id="u1", filename="f.pdf", storage_key="k", size_bytes=10)
    await repo.save_page_extracts(record.id, [make_extract(n, t) for n, t in pages])
    return repo, record.id


def _config(pdf_id: str) -> dict:
    return {"configurable": {"pdf_id": pdf_id}}


def _tool_by_name(tools: list, name: str):
    return next(t for t in tools if t.name == name)


@pytest.mark.asyncio
async def test_search_pages_ranks_by_term_overlap() -> None:
    repo, pdf_id = await _repo_with_pages(
        [(1, "the cat sat on the mat"), (2, "invoices and tax payments due")]
    )
    tools = make_pdf_tools(repo, top_k=1, char_limit=6000)
    search = _tool_by_name(tools, "search_pages")

    result = await search.ainvoke({"query": "tax invoice"}, _config(pdf_id))

    assert "[page 2]" in result
    assert "[page 1]" not in result


@pytest.mark.asyncio
async def test_search_pages_no_match_returns_message() -> None:
    repo, pdf_id = await _repo_with_pages([(1, "alpha beta gamma")])
    tools = make_pdf_tools(repo, top_k=3, char_limit=6000)
    search = _tool_by_name(tools, "search_pages")

    result = await search.ainvoke({"query": "zzz nonexistent"}, _config(pdf_id))

    assert "no matching pages" in result.lower()


@pytest.mark.asyncio
async def test_search_pages_truncates_to_char_limit() -> None:
    repo, pdf_id = await _repo_with_pages([(1, "word " * 1000)])
    tools = make_pdf_tools(repo, top_k=1, char_limit=50)
    search = _tool_by_name(tools, "search_pages")

    result = await search.ainvoke({"query": "word"}, _config(pdf_id))

    assert "truncated" in result.lower()


@pytest.mark.asyncio
async def test_get_page_returns_full_text() -> None:
    repo, pdf_id = await _repo_with_pages([(5, "content of page five")])
    tools = make_pdf_tools(repo, top_k=3, char_limit=6000)
    get_page = _tool_by_name(tools, "get_page")

    result = await get_page.ainvoke({"page_number": 5}, _config(pdf_id))

    assert "[page 5]" in result
    assert "content of page five" in result


@pytest.mark.asyncio
async def test_get_page_missing_returns_not_found() -> None:
    repo, pdf_id = await _repo_with_pages([(1, "only page")])
    tools = make_pdf_tools(repo, top_k=3, char_limit=6000)
    get_page = _tool_by_name(tools, "get_page")

    result = await get_page.ainvoke({"page_number": 9}, _config(pdf_id))

    assert "not found" in result.lower()


@pytest.mark.asyncio
async def test_search_pages_raises_when_pdf_id_missing() -> None:
    repo, _ = await _repo_with_pages([(1, "alpha beta gamma")])
    tools = make_pdf_tools(repo, top_k=3, char_limit=6000)
    search = _tool_by_name(tools, "search_pages")

    with pytest.raises(MissingPdfContextError):
        await search.ainvoke({"query": "x"}, {"configurable": {}})


@pytest.mark.asyncio
async def test_search_pages_breaks_ties_by_page_number() -> None:
    repo, pdf_id = await _repo_with_pages([(2, "tax"), (1, "tax")])
    tools = make_pdf_tools(repo, top_k=2, char_limit=6000)
    search = _tool_by_name(tools, "search_pages")

    result = await search.ainvoke({"query": "tax"}, _config(pdf_id))

    assert result.index("[page 1]") < result.index("[page 2]")
