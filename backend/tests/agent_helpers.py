from __future__ import annotations

from typing import Any

from app.parsing.types import PageExtract
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr


def make_extract(page_number: int, text: str, extractor: str = "pymupdf") -> PageExtract:
    return PageExtract(page_number=page_number, content_text=text, extractor=extractor)


class ScriptedChatModel(BaseChatModel):
    """A deterministic chat model that replays pre-built AI messages in order."""

    responses: list[BaseMessage]
    _index: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedChatModel:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        message = self.responses[self._index]
        self._index += 1
        return ChatResult(generations=[ChatGeneration(message=message)])
