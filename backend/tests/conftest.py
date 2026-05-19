from collections.abc import AsyncIterator

import pytest
from app.api.deps import get_file_storage, get_pdf_metadata_store
from app.config.settings import get_settings
from app.main import create_app
from app.metadata.factory import reset_metadata_store_state
from app.metadata.memory import InMemoryPdfMetadataStore
from app.storage.factory import reset_file_storage_state
from app.storage.memory import InMemoryFileStorage
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
async def _reset_metadata_factory() -> None:
    await reset_metadata_store_state()
    reset_file_storage_state()
    yield
    await reset_metadata_store_state()
    reset_file_storage_state()


@pytest.fixture
def file_storage() -> InMemoryFileStorage:
    """In-memory file storage for tests — not wired through create_file_storage()."""
    return InMemoryFileStorage()


@pytest.fixture
def pdf_metadata_store() -> InMemoryPdfMetadataStore:
    """In-memory metadata store for tests — not wired through create_pdf_metadata_store()."""
    return InMemoryPdfMetadataStore()


@pytest.fixture
async def api_client(
    file_storage: InMemoryFileStorage,
    pdf_metadata_store: InMemoryPdfMetadataStore,
) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_file_storage] = lambda: file_storage
    app.dependency_overrides[get_pdf_metadata_store] = lambda: pdf_metadata_store

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    app.dependency_overrides.clear()
