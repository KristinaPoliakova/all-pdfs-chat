from __future__ import annotations

import pytest
from app.agent.graph import build_agent_graph
from app.agent.tools import make_pdf_tools
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from tests.agent_helpers import ScriptedChatModel, make_extract


def _search_call(index: int, query: str) -> AIMessage:
    """An AI turn that only asks to search (no text), like a real tool-calling LLM."""
    return AIMessage(
        content="",
        tool_calls=[{"name": "search_pages", "args": {"query": query}, "id": f"c{index}"}],
    )


async def _repo_with_pages(pages: list[tuple[int, str]]) -> tuple[InMemoryPdfRepository, str]:
    repo = InMemoryPdfRepository()
    record = await repo.create(user_id="u1", filename="f.pdf", storage_key="k", size_bytes=10)
    await repo.save_page_extracts(record.id, [make_extract(n, t) for n, t in pages])
    return repo, record.id


@pytest.mark.asyncio
async def test_graph_returns_text_answer_after_tool_use() -> None:
    repo, pdf_id = await _repo_with_pages([(1, "Alice signed the contract")])
    model = ScriptedChatModel(
        responses=[
            _search_call(0, "Alice"),
            AIMessage(content="The person named is Alice [page 1]."),
        ]
    )
    graph = build_agent_graph(
        model=model,
        tools=list(make_pdf_tools(repo, top_k=3, char_limit=6000)),
        checkpointer=MemorySaver(),
        max_tool_iterations=5,
    )

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="whats the name")], "steps": 0, "cited_pages": []},
        {"configurable": {"thread_id": "t1", "pdf_id": pdf_id}},
    )

    assert result["messages"][-1].content == "The person named is Alice [page 1]."
    assert result["cited_pages"] == [1]


@pytest.mark.asyncio
async def test_graph_forces_text_answer_when_tool_iteration_limit_reached() -> None:
    # Regression: a vague query made the model search repeatedly without ever
    # answering. When the loop hit the tool-iteration cap, the trailing message
    # was an unexecuted tool call with empty content, so the user saw a blank box.
    # Now the final turn runs without tools, so the model must reply with text.
    repo, pdf_id = await _repo_with_pages([(1, "alpha beta gamma")])
    # Five fruitless searches exhaust the budget; the sixth turn must produce text.
    relentless_searches = [_search_call(i, "zzz-no-match") for i in range(5)]
    final_answer = AIMessage(content="I could not find that in this document.")
    model = ScriptedChatModel(responses=[*relentless_searches, final_answer])

    graph = build_agent_graph(
        model=model,
        tools=list(make_pdf_tools(repo, top_k=3, char_limit=6000)),
        checkpointer=MemorySaver(),
        max_tool_iterations=5,
    )

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="whats the name of person")],
            "steps": 0,
            "cited_pages": [],
        },
        {"configurable": {"thread_id": "t1", "pdf_id": pdf_id}},
    )

    final = result["messages"][-1]
    assert final.content == "I could not find that in this document."
    assert not getattr(final, "tool_calls", None)
    # Exactly the budgeted number of tool rounds ran, no more.
    assert result["steps"] == 5
