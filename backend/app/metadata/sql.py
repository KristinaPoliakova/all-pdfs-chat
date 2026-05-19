from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.metadata.protocol import PdfMetadataRecord
from app.models.pdf_document import PdfDocument


class SqlPdfMetadataStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def init(self) -> None:
        _ensure_sqlite_parent_dir(self._database_url)
        engine = self._get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._session_factory = None

    async def create(
        self,
        *,
        filename: str,
        storage_key: str,
        size_bytes: int,
    ) -> PdfMetadataRecord:
        document = PdfDocument(
            filename=filename,
            storage_key=storage_key,
            size_bytes=size_bytes,
        )
        factory = self._get_session_factory()
        async with factory() as session:
            try:
                session.add(document)
                await session.commit()
                await session.refresh(document)
            except Exception:
                await session.rollback()
                raise
        return _to_record(document)

    def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                self._database_url,
                echo=False,
                pool_pre_ping=True,
            )
        return self._engine

    def _get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self._get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    if "sqlite" not in database_url or "///" not in database_url:
        return

    raw_path = unquote(database_url.split("///", 1)[1].split("?", 1)[0])
    if not raw_path or raw_path == ":memory:":
        return

    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _to_record(document: PdfDocument) -> PdfMetadataRecord:
    return PdfMetadataRecord(
        id=document.id,
        filename=document.filename,
        storage_key=document.storage_key,
        size_bytes=document.size_bytes,
        created_at=document.created_at,
    )
