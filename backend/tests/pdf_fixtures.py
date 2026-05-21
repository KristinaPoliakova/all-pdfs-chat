from __future__ import annotations

import fitz


def make_text_pdf_bytes(*, pages: int = 1, text: str | None = None) -> bytes:
    doc = fitz.open()
    body = text or ("Sample digital PDF text for classification testing. " * 8)
    for _ in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), body)
    return doc.tobytes()
