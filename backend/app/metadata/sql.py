from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.classification.types import PageClassificationResult, PdfProcessingStatus
from app.db.base import Base
from app.metadata.protocol import PdfMetadataRecord
from app.models.pdf_document import PdfDocument
from app.models.pdf_page import PdfPage


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
        processing_status: PdfProcessingStatus = PdfProcessingStatus.UPLOADED,
    ) -> PdfMetadataRecord:
        document = PdfDocument(
            filename=filename,
            storage_key=storage_key,
            size_bytes=size_bytes,
            processing_status=processing_status.value,
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

    async def set_processing_status(
        self,
        pdf_id: str,
        status: PdfProcessingStatus,
        *,
        error: str | None = None,
    ) -> None:
        factory = self._get_session_factory()
        async with factory() as session:
            document = await session.get(PdfDocument, pdf_id)
            if document is None:
                raise LookupError(f"PDF document not found: {pdf_id}")
            document.processing_status = status.value
            document.classification_error = error
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def save_page_classifications(
        self,
        pdf_id: str,
        pages: list[PageClassificationResult],
        *,
        page_count: int,
        classified_at: datetime,
    ) -> None:
        factory = self._get_session_factory()
        async with factory() as session:
            document = await session.get(PdfDocument, pdf_id)
            if document is None:
                raise LookupError(f"PDF document not found: {pdf_id}")
            await session.execute(
                delete(PdfPage).where(PdfPage.pdf_document_id == pdf_id),
            )
            for page in pages:
                session.add(
                    PdfPage(
                        pdf_document_id=pdf_id,
                        page_number=page.page_number,
                        page_class=page.page_class.value,
                        confidence=page.confidence,
                        signals_json=page.signals_json,
                    ),
                )
            document.page_count = page_count
            document.classified_at = classified_at
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get(self, pdf_id: str) -> PdfMetadataRecord:
        factory = self._get_session_factory()
        async with factory() as session:
            document = await session.get(PdfDocument, pdf_id)
            if document is None:
                raise LookupError(f"PDF document not found: {pdf_id}")
        return _to_record(document)

    async def get_pages(self, pdf_id: str) -> list[PageClassificationResult]:
        factory = self._get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(PdfPage)
                .where(PdfPage.pdf_document_id == pdf_id)
                .order_by(PdfPage.page_number),
            )
            rows = result.scalars().all()
        return [_to_page_result(row) for row in rows]

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
        processing_status=PdfProcessingStatus(document.processing_status),
        page_count=document.page_count,
        classification_error=document.classification_error,
        classified_at=document.classified_at,
    )


def _to_page_result(page: PdfPage) -> PageClassificationResult:
    from app.classification.types import PageClass

    return PageClassificationResult(
        page_number=page.page_number,
        page_class=PageClass(page.page_class),
        confidence=page.confidence,
        signals_json=page.signals_json,
    )
