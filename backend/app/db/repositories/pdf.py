from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from app.classification.types import PageClassificationResult, PdfProcessingStatus
from app.core.datetime_utils import ensure_utc
from app.db.base import Base
from app.db.engine import create_app_async_engine
from app.db.models.pdf_document import PdfDocument
from app.db.models.pdf_page import PdfPage
from app.db.models.pdf_page_extract import PdfPageExtract
from app.db.sqlite_paths import sqlite_file_path
from app.parsing.types import PageExtract
from app.pdf_repository.protocol import PdfRecord


class SqlPdfRepository:
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
    ) -> PdfRecord:
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
            _apply_processing_status(document, status, error=error)
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

    async def get(self, pdf_id: str) -> PdfRecord:
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

    async def save_page_extracts(
        self,
        pdf_id: str,
        extracts: list[PageExtract],
    ) -> None:
        factory = self._get_session_factory()
        async with factory() as session:
            document = await session.get(PdfDocument, pdf_id)
            if document is None:
                raise LookupError(f"PDF document not found: {pdf_id}")
            await session.execute(
                delete(PdfPageExtract).where(PdfPageExtract.pdf_document_id == pdf_id),
            )
            for extract in extracts:
                session.add(
                    PdfPageExtract(
                        pdf_document_id=pdf_id,
                        page_number=extract.page_number,
                        extractor=extract.extractor,
                        content_text=extract.content_text,
                    ),
                )
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_page_extracts(self, pdf_id: str) -> list[PageExtract]:
        factory = self._get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(PdfPageExtract)
                .where(PdfPageExtract.pdf_document_id == pdf_id)
                .order_by(PdfPageExtract.page_number),
            )
            rows = result.scalars().all()
        return [_to_page_extract(row) for row in rows]

    def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_app_async_engine(self._database_url)
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
    db_path = sqlite_file_path(database_url)
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)


def _to_record(document: PdfDocument) -> PdfRecord:
    return PdfRecord(
        id=document.id,
        filename=document.filename,
        storage_key=document.storage_key,
        size_bytes=document.size_bytes,
        created_at=ensure_utc(document.created_at),
        processing_status=PdfProcessingStatus(document.processing_status),
        page_count=document.page_count,
        classification_error=document.classification_error,
        classified_at=(
            ensure_utc(document.classified_at) if document.classified_at is not None else None
        ),
        parsing_error=document.parsing_error,
        parsed_at=ensure_utc(document.parsed_at) if document.parsed_at is not None else None,
    )


def _apply_processing_status(
    document: PdfDocument,
    status: PdfProcessingStatus,
    *,
    error: str | None,
) -> None:
    document.processing_status = status.value
    if status in {
        PdfProcessingStatus.CLASSIFYING,
        PdfProcessingStatus.CLASSIFICATION_FAILED,
    }:
        document.classification_error = error
    elif status in {PdfProcessingStatus.PARSING, PdfProcessingStatus.PARSING_FAILED}:
        document.parsing_error = error
    elif status == PdfProcessingStatus.PARSED:
        document.parsed_at = datetime.now(UTC)
        document.parsing_error = None


def _to_page_extract(row: PdfPageExtract) -> PageExtract:
    return PageExtract(
        page_number=row.page_number,
        content_text=row.content_text,
        extractor=row.extractor,
    )


def _to_page_result(page: PdfPage) -> PageClassificationResult:
    from app.classification.types import PageClass

    return PageClassificationResult(
        page_number=page.page_number,
        page_class=PageClass(page.page_class),
        confidence=page.confidence,
        signals_json=page.signals_json,
    )
