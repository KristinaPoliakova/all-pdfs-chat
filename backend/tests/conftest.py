from __future__ import annotations

import os

# app.main creates the FastAPI app at import time; override developer .env before importing app.
os.environ["APP_ENV"] = "dev"
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://all_pdfs_chat:devpassword@127.0.0.1:5432/all_pdfs_chat_test"
)
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = ""
os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = ""
os.environ["AZURE_DOCUMENT_INTELLIGENCE_API_KEY"] = ""
os.environ["PARSING_ENABLED"] = "false"

from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from app.api.deps import get_file_storage, get_job_queue, get_pdf_repository
from app.application.auth.deps import get_session_repository, get_user_repository
from app.classification.service import PdfClassificationService
from app.config.settings import Settings, get_settings
from app.infrastructure.factories.jobs import reset_job_queue_state
from app.infrastructure.factories.pdf import reset_pdf_repository_state
from app.infrastructure.factories.sessions import reset_session_repository_state
from app.infrastructure.factories.storage import reset_file_storage_state
from app.infrastructure.factories.users import reset_user_repository_state
from app.infrastructure.persistence.memory.jobs import InMemoryJobQueue
from app.infrastructure.persistence.memory.pdf import InMemoryPdfRepository
from app.infrastructure.persistence.memory.sessions import InMemorySessionRepository
from app.infrastructure.persistence.memory.users import InMemoryUserRepository
from app.infrastructure.persistence.sql.lifecycle import reset_database_state
from app.infrastructure.storage.memory import InMemoryFileStorage
from app.main import create_app
from app.parsing.composite import CompositeDocumentParser
from app.worker.pdf_pipeline import PdfProcessingPipeline
from httpx import ASGITransport, AsyncClient

from tests.auth_helpers import register_and_get_auth_headers
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
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    monkeypatch.setenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
    monkeypatch.setenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY", "")
    monkeypatch.setenv("PARSING_ENABLED", "false")


@pytest.fixture(autouse=True)
async def _reset_pdf_repository_factory() -> None:
    await reset_database_state()
    await reset_pdf_repository_state()
    await reset_job_queue_state()
    await reset_user_repository_state()
    await reset_session_repository_state()
    reset_file_storage_state()
    yield
    await reset_database_state()
    await reset_pdf_repository_state()
    await reset_job_queue_state()
    await reset_user_repository_state()
    await reset_session_repository_state()
    reset_file_storage_state()


@pytest.fixture
def file_storage() -> InMemoryFileStorage:
    """In-memory file storage for tests — not wired through create_file_storage()."""
    return InMemoryFileStorage()


@pytest.fixture
def job_queue() -> InMemoryJobQueue:
    return InMemoryJobQueue()


@pytest.fixture
def pdf_repository() -> InMemoryPdfRepository:
    """In-memory pdf store for tests — not wired through create_pdf_repository()."""
    return InMemoryPdfRepository()


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def session_repository() -> InMemorySessionRepository:
    return InMemorySessionRepository()


@pytest.fixture
async def auth_headers(api_client: AsyncClient) -> dict[str, str]:
    return await register_and_get_auth_headers(api_client)


@pytest.fixture
async def api_client(
    file_storage: InMemoryFileStorage,
    pdf_repository: InMemoryPdfRepository,
    job_queue: InMemoryJobQueue,
    user_repository: InMemoryUserRepository,
    session_repository: InMemorySessionRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    get_settings.cache_clear()

    async def _skip_init_database(settings: Settings | None = None) -> None:
        return None

    def _get_test_settings() -> Settings:
        return make_test_settings()

    monkeypatch.setattr("app.main.init_database", _skip_init_database)
    monkeypatch.setattr("app.main.get_settings", _get_test_settings)
    monkeypatch.setattr("app.config.settings.get_settings", _get_test_settings)
    monkeypatch.setattr(
        "app.infrastructure.persistence.sql.lifecycle.get_settings",
        _get_test_settings,
    )
    monkeypatch.setattr("app.infrastructure.factories.jobs.get_settings", _get_test_settings)
    monkeypatch.setattr(
        "app.infrastructure.factories.storage.get_settings",
        _get_test_settings,
    )

    app = create_app()
    app.dependency_overrides[get_settings] = _get_test_settings
    app.dependency_overrides[get_file_storage] = lambda: file_storage
    app.dependency_overrides[get_pdf_repository] = lambda: pdf_repository
    app.dependency_overrides[get_job_queue] = lambda: job_queue
    app.dependency_overrides[get_user_repository] = lambda: user_repository
    app.dependency_overrides[get_session_repository] = lambda: session_repository

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    app.dependency_overrides.clear()


@pytest.fixture
def run_pending_pdf_jobs(
    file_storage: InMemoryFileStorage,
    pdf_repository: InMemoryPdfRepository,
    job_queue: InMemoryJobQueue,
) -> Callable[[], Awaitable[None]]:
    settings = make_test_settings(classification_enabled=True, parsing_enabled=False)

    async def _run() -> None:
        pipeline = PdfProcessingPipeline(
            pdf_repository=pdf_repository,
            storage=file_storage,
            settings=settings,
            classifier=PdfClassificationService(settings=settings),
            parser=CompositeDocumentParser(settings=settings),
        )
        while True:
            job = await job_queue.claim_next(worker_id="test-worker")
            if job is None:
                break
            await pipeline.run(job.pdf_document_id)
            await job_queue.complete(job.id)

    return _run


@pytest.fixture
async def drain_pdf_jobs(
    run_pending_pdf_jobs: Callable[[], Awaitable[None]],
) -> Callable[[], Awaitable[None]]:
    return run_pending_pdf_jobs
