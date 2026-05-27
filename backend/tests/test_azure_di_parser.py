from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from app.classification.service import PdfClassificationService
from app.classification.types import PageClass, PageClassificationResult, PdfProcessingStatus
from app.config.settings import Settings
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository
from app.infrastructure.storage.memory import InMemoryFileStorage
from app.parsing.azure_di import AzureDocumentIntelligenceParser, format_azure_pages_parameter
from app.parsing.composite import CompositeDocumentParser
from app.parsing.factory import create_document_parser
from app.parsing.types import PageExtract
from app.worker.pdf_pipeline import PdfProcessingPipeline

from tests.pdf_fixtures import make_text_pdf_bytes
from tests.settings_helpers import make_test_settings


@dataclass
class _FakeLine:
    content: str


@dataclass
class _FakePage:
    page_number: int
    lines: list[_FakeLine] = field(default_factory=list)


@dataclass
class _FakeAnalyzeResult:
    pages: list[_FakePage]


class _FakePoller:
    def __init__(
        self,
        result: _FakeAnalyzeResult,
        *,
        done_after_polls: int = 0,
        fail_message: str | None = None,
    ) -> None:
        self._result = result
        self._done_after_polls = done_after_polls
        self._poll_count = 0
        self._fail_message = fail_message
        self.cancelled = False

    def done(self) -> bool:
        if self._done_after_polls == 0:
            return True
        self._poll_count += 1
        return self._poll_count > self._done_after_polls

    def result(self) -> _FakeAnalyzeResult:
        if self._fail_message is not None:
            raise RuntimeError(self._fail_message)
        return self._result

    def cancel(self) -> None:
        self.cancelled = True


class _FakeDocumentIntelligenceClient:
    def __init__(self, poller: _FakePoller) -> None:
        self._poller = poller
        self.last_request: Any | None = None
        self.last_pages: str | None = None

    def begin_analyze_document(
        self,
        model_id: str,
        request: Any,
        *,
        pages: str | None = None,
        **kwargs: Any,
    ) -> _FakePoller:
        self.last_request = request
        self.last_pages = pages
        assert model_id == "prebuilt-read"
        return self._poller


def test_format_azure_pages_parameter_groups_consecutive_pages() -> None:
    assert format_azure_pages_parameter([2]) == "2"
    assert format_azure_pages_parameter([1, 2, 3, 5, 7]) == "1-3,5,7"
    assert format_azure_pages_parameter([3, 1, 2]) == "1-3"


@pytest.mark.asyncio
async def test_parse_pages_returns_text_for_requested_pages() -> None:
    poller = _FakePoller(
        _FakeAnalyzeResult(
            pages=[
                _FakePage(page_number=1, lines=[_FakeLine(content="Page one")]),
                _FakePage(
                    page_number=2,
                    lines=[_FakeLine(content="Line A"), _FakeLine(content="Line B")],
                ),
            ],
        ),
    )
    client = _FakeDocumentIntelligenceClient(poller)
    settings = make_test_settings(
        parsing_enabled=True,
        azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com",
        azure_document_intelligence_api_key="test-key",
    )
    parser = AzureDocumentIntelligenceParser(settings=settings, client=client)

    extracts = await parser.parse_pages(b"%PDF", page_numbers=[2])

    assert client.last_pages == "2"
    assert extracts == [
        PageExtract(
            page_number=2,
            content_text="Line A\nLine B",
            extractor="azure_document_intelligence",
        ),
    ]


@pytest.mark.asyncio
async def test_parse_pages_requests_only_specified_pages_from_azure() -> None:
    poller = _FakePoller(_FakeAnalyzeResult(pages=[]))
    client = _FakeDocumentIntelligenceClient(poller)
    settings = make_test_settings(
        parsing_enabled=True,
        azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com",
        azure_document_intelligence_api_key="test-key",
    )
    parser = AzureDocumentIntelligenceParser(settings=settings, client=client)

    await parser.parse_pages(b"%PDF", page_numbers=[2, 3, 5, 7, 8])

    assert client.last_pages == "2-3,5,7-8"


@pytest.mark.asyncio
async def test_parse_pages_timeout_raises() -> None:
    poller = _FakePoller(_FakeAnalyzeResult(pages=[]), done_after_polls=100)
    client = _FakeDocumentIntelligenceClient(poller)
    settings = Settings.model_construct(
        parsing_enabled=True,
        azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com",
        azure_document_intelligence_api_key="test-key",
        parsing_poll_interval_seconds=0.01,
        parsing_max_wait_seconds=0,
    )
    parser = AzureDocumentIntelligenceParser(settings=settings, client=client)

    with pytest.raises(TimeoutError, match="timed out"):
        await parser.parse_pages(b"%PDF", page_numbers=[1])


@pytest.mark.asyncio
async def test_pipeline_sets_parsing_failed_on_azure_timeout() -> None:
    poller = _FakePoller(_FakeAnalyzeResult(pages=[]), done_after_polls=100)
    client = _FakeDocumentIntelligenceClient(poller)
    settings = Settings.model_construct(
        classification_enabled=False,
        parsing_enabled=True,
        azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com",
        azure_document_intelligence_api_key="test-key",
        parsing_poll_interval_seconds=0.01,
        parsing_max_wait_seconds=0,
    )
    pdf_repository = InMemoryPdfRepository()
    file_storage = InMemoryFileStorage()
    data = make_text_pdf_bytes(pages=1)
    storage_key = "pdfs/timeout.pdf"
    file_storage.upload(storage_key, data)
    record = await pdf_repository.create(
        user_id="user-1",
        filename="timeout.pdf",
        storage_key=storage_key,
        size_bytes=len(data),
    )
    await pdf_repository.save_page_classifications(
        record.id,
        [
            PageClassificationResult(
                page_number=1,
                page_class=PageClass.BORN_DIGITAL_COMPLEX,
                confidence=0.9,
            ),
        ],
        page_count=1,
        classified_at=record.created_at,
    )
    await pdf_repository.set_processing_status(record.id, PdfProcessingStatus.CLASSIFIED)

    parser = CompositeDocumentParser(
        settings=settings,
        azure_parser=AzureDocumentIntelligenceParser(settings=settings, client=client),
    )

    pipeline = PdfProcessingPipeline(
        pdf_repository=pdf_repository,
        storage=file_storage,
        settings=settings,
        classifier=PdfClassificationService(settings=settings),
        parser=parser,
    )

    extract_count = await pipeline._phase_parse(record.id, data, {})

    assert extract_count == 0
    updated = await pdf_repository.get(record.id)
    assert updated.processing_status == PdfProcessingStatus.PARSING_FAILED
    assert updated.parsing_error is not None
    assert "timed out" in updated.parsing_error.lower()


def test_create_document_parser_without_azure_when_disabled() -> None:
    settings = make_test_settings(parsing_enabled=False)

    parser = create_document_parser(settings)

    assert isinstance(parser, CompositeDocumentParser)
    assert parser._azure_parser is None


def test_create_document_parser_wires_azure_when_enabled() -> None:
    settings = make_test_settings(
        parsing_enabled=True,
        azure_document_intelligence_endpoint="https://example.cognitiveservices.azure.com",
        azure_document_intelligence_api_key="test-key",
    )

    parser = create_document_parser(settings)

    assert isinstance(parser, CompositeDocumentParser)
    assert isinstance(parser._azure_parser, AzureDocumentIntelligenceParser)
