from __future__ import annotations

import uuid

import psycopg
import pytest
from app.agent.graph import build_agent_graph
from app.config.settings import Settings
from app.infrastructure.factories.chat_checkpointer import (
    _to_psycopg_conninfo,
    close_chat_checkpointer,
    get_chat_checkpointer,
    init_chat_checkpointer,
)
from langchain_core.messages import AIMessage, HumanMessage

from tests.agent_helpers import ScriptedChatModel
from tests.settings_helpers import make_test_settings

_LANGGRAPH_TABLES = (
    "checkpoint_writes",
    "checkpoint_blobs",
    "checkpoints",
    "checkpoint_migrations",
)


async def _drop_langgraph_tables(settings: Settings) -> None:
    """Keep the shared test DB clean so migration table-set assertions stay valid."""
    conninfo = _to_psycopg_conninfo(settings.database_url)
    async with await psycopg.AsyncConnection.connect(conninfo, autocommit=True) as conn:
        await conn.execute(
            f"DROP TABLE IF EXISTS {', '.join(_LANGGRAPH_TABLES)} CASCADE"  # noqa: S608
        )


@pytest.mark.asyncio
async def test_postgres_checkpointer_persists_conversation() -> None:
    settings = make_test_settings()
    await init_chat_checkpointer(settings)
    try:
        checkpointer = get_chat_checkpointer()
        model = ScriptedChatModel(
            responses=[AIMessage(content="first"), AIMessage(content="second")]
        )
        graph = build_agent_graph(
            model=model, tools=[], checkpointer=checkpointer, max_tool_iterations=2
        )
        config = {"configurable": {"thread_id": str(uuid.uuid4()), "pdf_id": "p"}}

        await graph.ainvoke(
            {"messages": [HumanMessage(content="hi")], "steps": 0, "cited_pages": []}, config
        )
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="again")], "steps": 0, "cited_pages": []}, config
        )

        assert len(result["messages"]) == 4
    finally:
        await close_chat_checkpointer()
        await _drop_langgraph_tables(settings)
