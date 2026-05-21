from __future__ import annotations

import fitz  # type: ignore[import-untyped]

from app.parsing.types import PageExtract


def extract_page_text(data: bytes, page_numbers: list[int]) -> list[PageExtract]:
    if not page_numbers:
        return []
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        extracts: list[PageExtract] = []
        for page_number in sorted(page_numbers):
            if page_number < 1 or page_number > doc.page_count:
                msg = f"Page number {page_number} is out of range"
                raise ValueError(msg)
            page = doc.load_page(page_number - 1)
            text = page.get_text().strip()
            extracts.append(
                PageExtract(
                    page_number=page_number,
                    content_text=text,
                    extractor="local_pymupdf",
                ),
            )
        return extracts
    finally:
        doc.close()
