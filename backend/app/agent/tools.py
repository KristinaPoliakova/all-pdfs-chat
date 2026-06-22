from __future__ import annotations

import re
from collections.abc import Sequence

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool

from app.agent.exceptions import MissingPdfContextError
from app.application.ports.pdf import PdfRepository
from app.parsing.types import PageExtract

_WORD_RE = re.compile(r"\w+")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _score(query_terms: set[str], page_text: str) -> int:
    if not query_terms:
        return 0
    page_terms = set(_tokens(page_text))
    return len(query_terms & page_terms)


def _truncate(text: str, char_limit: int) -> str:
    if len(text) <= char_limit:
        return text
    return text[:char_limit] + "\n…[truncated]"


def _format_page(extract: PageExtract, char_limit: int) -> str:
    return f"[page {extract.page_number}]\n{_truncate(extract.content_text, char_limit)}"


def _pdf_id(config: RunnableConfig) -> str:
    configurable = config.get("configurable") or {}
    pdf_id = configurable.get("pdf_id")
    if not isinstance(pdf_id, str) or not pdf_id:
        raise MissingPdfContextError("pdf_id missing from RunnableConfig.configurable")
    return pdf_id


def make_pdf_tools(
    repository: PdfRepository,
    *,
    top_k: int,
    char_limit: int,
) -> Sequence[BaseTool]:
    @tool
    async def search_pages(query: str, config: RunnableConfig) -> str:
        """Search the document's pages for text relevant to the query.

        Returns the most relevant pages, each prefixed with its page number.
        Use this to find where a topic is discussed.
        """
        extracts = await repository.get_page_extracts(_pdf_id(config))
        query_terms = set(_tokens(query))
        scored = [(extract, _score(query_terms, extract.content_text)) for extract in extracts]
        matches = sorted(
            (pair for pair in scored if pair[1] > 0),
            key=lambda pair: (-pair[1], pair[0].page_number),
        )[:top_k]
        if not matches:
            return "No matching pages found for that query."
        return "\n\n".join(_format_page(extract, char_limit) for extract, _ in matches)

    @tool
    async def get_page(page_number: int, config: RunnableConfig) -> str:
        """Return the full text of one page, identified by its page number."""
        extracts = await repository.get_page_extracts(_pdf_id(config))
        for extract in extracts:
            if extract.page_number == page_number:
                return _format_page(extract, char_limit)
        return f"Page {page_number} was not found in this document."

    return [search_pages, get_page]
