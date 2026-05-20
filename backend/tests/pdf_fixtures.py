from __future__ import annotations

import fitz


def make_text_pdf_bytes(*, pages: int = 1) -> bytes:
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), "Sample digital PDF text for classification testing. " * 8)
    return doc.tobytes()
