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

from app.agent.prompts import FORCE_ANSWER_INSTRUCTION, SYSTEM_PROMPT
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
        # Once the tool budget is spent, call the model WITHOUT tools so it can only
        # reply with text. This guarantees a final answer instead of looping into
        # another (unexecuted) tool call that would surface to the user as a blank
        # response.
        tools_exhausted = state["steps"] >= max_tool_iterations
        prompt: list[AnyMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
        if tools_exhausted:
            prompt.append(SystemMessage(content=FORCE_ANSWER_INSTRUCTION))
        prompt.extend(state["messages"])
        llm = model if tools_exhausted else model_with_tools
        response = await llm.ainvoke(prompt)
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
        # The agent node stops requesting tools once the budget is spent (it is
        # called without tools then), so a tool-call message here always means we
        # still have budget to run them.
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tools_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    return builder.compile(checkpointer=checkpointer)
