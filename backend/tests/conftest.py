from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from app.api.deps import get_file_storage, get_job_queue, get_pdf_metadata_store
from app.classification.service import PdfClassificationService
from app.config.settings import Settings, get_settings
from app.jobs.factory import reset_job_queue_state
from app.jobs.memory import InMemoryJobQueue
from app.main import create_app
from app.metadata.factory import reset_metadata_store_state
from app.metadata.memory import InMemoryPdfMetadataStore
from app.parsing.composite import CompositeDocumentParser
from app.storage.factory import reset_file_storage_state
from app.storage.memory import InMemoryFileStorage
from app.worker.pdf_pipeline import PdfProcessingPipeline
from httpx import ASGITransport, AsyncClient

from tests.settings_helpers import TEST_DATABASE_URL, make_test_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _isolate_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep pytest off developer .env / shell prod credentials."""
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("AZURE_SQL_CONNECTIONSTRING", "")
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    monkeypatch.setenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
    monkeypatch.setenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY", "")
    monkeypatch.setenv("PARSING_ENABLED", "false")


@pytest.fixture(autouse=True)
async def _reset_metadata_factory() -> None:
    await reset_metadata_store_state()
    await reset_job_queue_state()
    reset_file_storage_state()
    yield
    await reset_metadata_store_state()
    await reset_job_queue_state()
    reset_file_storage_state()


@pytest.fixture
def file_storage() -> InMemoryFileStorage:
    """In-memory file storage for tests — not wired through create_file_storage()."""
    return InMemoryFileStorage()


@pytest.fixture
def job_queue() -> InMemoryJobQueue:
    return InMemoryJobQueue()


@pytest.fixture
def pdf_metadata_store() -> InMemoryPdfMetadataStore:
    """In-memory metadata store for tests — not wired through create_pdf_metadata_store()."""
    return InMemoryPdfMetadataStore()


@pytest.fixture
async def api_client(
    file_storage: InMemoryFileStorage,
    pdf_metadata_store: InMemoryPdfMetadataStore,
    job_queue: InMemoryJobQueue,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    get_settings.cache_clear()

    def _get_test_settings() -> Settings:
        return make_test_settings()

    monkeypatch.setattr("app.main.get_settings", _get_test_settings)
    monkeypatch.setattr("app.config.settings.get_settings", _get_test_settings)
    monkeypatch.setattr("app.metadata.factory.get_settings", _get_test_settings)
    monkeypatch.setattr("app.jobs.factory.get_settings", _get_test_settings)
    monkeypatch.setattr("app.storage.factory.get_settings", _get_test_settings)

    app = create_app()
    app.dependency_overrides[get_settings] = _get_test_settings
    app.dependency_overrides[get_file_storage] = lambda: file_storage
    app.dependency_overrides[get_pdf_metadata_store] = lambda: pdf_metadata_store
    app.dependency_overrides[get_job_queue] = lambda: job_queue

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    app.dependency_overrides.clear()


@pytest.fixture
def run_pending_pdf_jobs(
    file_storage: InMemoryFileStorage,
    pdf_metadata_store: InMemoryPdfMetadataStore,
    job_queue: InMemoryJobQueue,
) -> Callable[[], Awaitable[None]]:
    settings = make_test_settings(classification_enabled=True, parsing_enabled=False)

    async def _run() -> None:
        pipeline = PdfProcessingPipeline(
            metadata_store=pdf_metadata_store,
            storage=file_storage,
            settings=settings,
            classifier=PdfClassificationService(settings=settings),
            parser=CompositeDocumentParser(settings=settings),
        )
        while True:
            job = await job_queue.claim_next(worker_id="test-worker")
            if job is None:
                break
            await pipeline.run(job.pdf_id)
            await job_queue.complete(job.id)

    return _run


@pytest.fixture
async def drain_pdf_jobs(
    run_pending_pdf_jobs: Callable[[], Awaitable[None]],
) -> Callable[[], Awaitable[None]]:
    return run_pending_pdf_jobs
