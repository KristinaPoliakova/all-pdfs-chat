from __future__ import annotations

import operator
import re
from typing import Annotated, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tracing import trace_node

_PAGE_MARKER = re.compile(r"\[page (\d+)\]")


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    steps: int
    cited_pages: Annotated[list[int], operator.add]


def build_agent_graph(
    *,
    model: BaseChatModel,
    tools: list[BaseTool],
    checkpointer: BaseCheckpointSaver[Any],
    max_tool_iterations: int,
) -> CompiledStateGraph[AgentState, Any, Any, Any]:
    model_with_tools = model.bind_tools(tools)
    tool_node = ToolNode(tools)

    @trace_node("agent_node", "LLM")
    async def agent_node(state: AgentState) -> dict[str, Any]:
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    @trace_node("tools_node", "TOOL")
    async def tools_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        result = await tool_node.ainvoke(state, config)
        tool_messages = result["messages"]
        cited: list[int] = []
        for message in tool_messages:
            text = message.content if isinstance(message.content, str) else str(message.content)
            cited.extend(int(match) for match in _PAGE_MARKER.findall(text))
        return {
            "messages": tool_messages,
            "steps": state["steps"] + 1,
            "cited_pages": cited,
        }

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        has_calls = bool(getattr(last, "tool_calls", None))
        if has_calls and state["steps"] < max_tool_iterations:
            return "tools"
        return END

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tools_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    return builder.compile(checkpointer=checkpointer)
