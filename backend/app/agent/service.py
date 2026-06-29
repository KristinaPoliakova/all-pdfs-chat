from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agent.exceptions import AgentTimeoutError, AgentUnavailableError
from app.agent.graph import build_agent_graph
from app.agent.tools import make_pdf_tools
from app.agent.tracing import agent_trace
from app.application.ports.chat import ChatAnswer
from app.application.ports.pdf import PdfRepository
from app.config.settings import Settings

logger = logging.getLogger(__name__)

_EMPTY_DOCUMENT_ANSWER = "No readable text was found in this document."
_NO_ANSWER_FALLBACK = "I could not find an answer to that in this document."


class LangGraphChatService:
    def __init__(
        self,
        *,
        repository: PdfRepository,
        model: BaseChatModel,
        checkpointer: BaseCheckpointSaver[Any],
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._timeout = settings.agent_timeout_seconds
        self._app_env = settings.app_env
        tools = list(
            make_pdf_tools(
                repository,
                top_k=settings.agent_search_top_k,
                char_limit=settings.agent_tool_char_limit,
            )
        )
        self._graph = build_agent_graph(
            model=model,
            tools=tools,
            checkpointer=checkpointer,
            max_tool_iterations=settings.agent_max_tool_iterations,
        )

    async def answer(
        self, *, conversation_id: str, pdf_id: str, user_id: str, message: str
    ) -> ChatAnswer:
        with agent_trace(
            user_id=user_id,
            conversation_id=conversation_id,
            pdf_id=pdf_id,
            app_env=self._app_env,
            message=message,
        ) as trace:
            extracts = await self._repository.get_page_extracts(pdf_id)
            if not extracts:
                answer = ChatAnswer(answer=_EMPTY_DOCUMENT_ANSWER, citations=[], recorded=False)
                trace.set_outputs({"answer": answer.answer, "citations": answer.citations})
                return answer

            config: RunnableConfig = {
                "configurable": {"thread_id": conversation_id, "pdf_id": pdf_id}
            }
            inputs: dict[str, Any] = {
                "messages": [HumanMessage(content=message)],
                "steps": 0,
                "cited_pages": [],
            }
            try:
                result = await asyncio.wait_for(
                    self._graph.ainvoke(inputs, config),
                    timeout=self._timeout,
                )
            except TimeoutError as exc:
                raise AgentTimeoutError("The assistant took too long to respond.") from exc
            except Exception as exc:
                logger.exception("Agent run failed for conversation_id=%s", conversation_id)
                raise AgentUnavailableError("The assistant is temporarily unavailable.") from exc

            answer_text = _message_text(result["messages"][-1].content).strip()
            if not answer_text:
                # Last-resort guard so a blank message never reaches the UI even if
                # the model returns empty text despite the force-answer step.
                answer_text = _NO_ANSWER_FALLBACK
            citations = sorted(set(result.get("cited_pages", [])))
            answer = ChatAnswer(answer=answer_text, citations=citations)
            trace.set_outputs({"answer": answer.answer, "citations": answer.citations})
            return answer


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text", "")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(parts)
    return str(content)
