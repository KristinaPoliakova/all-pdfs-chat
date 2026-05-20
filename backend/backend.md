# Backend

Python **3.14**, **`uv`**, async **FastAPI**, **pytest** + **httpx** for API tests.

## Run locally

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

- API docs: http://127.0.0.1:8000/docs  
- Health: `GET /health`, `GET /ready` (readiness for orchestrators)  
- Upload: `POST /api/v1/pdfs` — multipart field `file` (PDF only); response includes `Location: /api/v1/pdfs/{id}`
- Read: `GET /api/v1/pdfs/{id}` — document metadata (no `pages`)
- Read: `GET /api/v1/pdfs/{id}/pages` — per-page classification

## Config

- File: `backend/.env` (template: `.env.example`)
- Code: `app/config/settings.py` → **`get_settings()`** is a cached singleton (`get_settings.cache_clear()` in tests)

| Variable | Notes |
|----------|--------|
| `APP_ENV` | `dev` or `prod` — picks storage + DB backends |
| `DATABASE_URL` | Dev SQLite (default `sqlite+aiosqlite:///./data/app.db`) |
| `AZURE_SQL_DATABASE_URL` | Prod metadata DB (required when `APP_ENV=prod`) |
| `MAX_UPLOAD_SIZE_BYTES` | Default 10 MiB |
| `AZURE_STORAGE_*` | Prod blob storage (required when `APP_ENV=prod`) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins; empty disables CORS |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default `INFO`) |

Local PDF folder is **not** in `.env` — fixed at `data/uploads/` (`LOCAL_STORAGE_PATH` in settings).

## `APP_ENV` wiring

| | `dev` | `prod` |
|---|--------|--------|
| PDF bytes | `app/storage/` → disk | Azure Blob |
| Metadata | `app/metadata/` → SQLite | Azure SQL |

- `create_file_storage()` and `create_pdf_metadata_store()` are **singletons** per process (reuse Azure clients / DB engine).
- **Prod SQL driver:** `uv sync --group prod` installs `aioodbc` for `mssql+aioodbc://` URLs.
- **Tests:** `InMemoryFileStorage` / `InMemoryPdfMetadataStore` only via FastAPI `dependency_overrides` in `tests/conftest.py` — never in `.env`.

## Code map (upload slice)

```
app/storage/     FileStorage protocol + local / azure / memory (tests)
app/metadata/    PdfMetadataStore protocol + sql / memory (tests)
app/services/pdf_upload.py   validation, size limit, orchestration
app/api/deps.py              inject storage + metadata store
app/api/routes/pdfs.py       POST handler
app/models/pdf_document.py   SQLAlchemy table (used by SqlPdfMetadataStore)
app/models/pdf_page.py       per-page classification rows
app/classification/          page routing rules (PyMuPDF + pdfplumber features)
```

## Page classification (PR1)

- **Tables:** `pdf_documents` (+ `processing_status`, `page_count`, …), `pdf_pages` (`page_class`, `confidence`, …)
- **Statuses:** `uploaded` → (future: `classifying`) → `classified` or `classification_failed`
- **Page classes:** `born_digital_simple`, `born_digital_complex` (image-heavy / low-text pages → `born_digital_complex`)
- **Deps:** `pymupdf`, `pdfplumber` only

After schema changes locally, delete `data/app.db` or run against a fresh DB so `create_all` picks up new columns/tables.

**Upload + classification:** `POST /api/v1/pdfs` stores the file, sets `processing_status=uploaded`, runs per-page classification (when `CLASSIFICATION_ENABLED=true`), then sets `classified` or `classification_failed`. Always returns **201**; failed classification leaves no `pdf_pages` rows.

| Variable | Default | Notes |
|----------|---------|--------|
| `CLASSIFICATION_ENABLED` | `true` | Set `false` to skip classification (stays `uploaded`) |
| `CLASSIFICATION_MAX_PAGES` | `500` | Rejects larger PDFs with `classification_failed` |

**Do not reintroduce** `app/repositories/` or route-level `get_db_session` — metadata goes through `PdfMetadataStore`.

## Startup vs upload

- **Startup:** `init()` on metadata store creates SQL tables (`data/app.db`).
- **First upload:** creates `data/uploads/pdfs/...` on disk (no prep step for file storage).

## Pre-commit (Ruff on every commit)

One-time setup from the **repo root**:

```bash
cd backend && uv sync
cd .. && uv run --directory backend pre-commit install
```

Each `git commit` runs Ruff lint (with `--fix`) and Ruff format on staged `backend/**/*.py` files.

Run on all backend Python files without committing:

```bash
uv run --directory backend pre-commit run --all-files
```

Bypass in an emergency only: `git commit --no-verify`.

## Checks

```bash
uv run pytest -q
uv run ruff check app tests
uv run mypy app
```

```bash
sqlite3 data/app.db "SELECT id, filename, storage_key FROM pdf_documents;"
ls data/uploads/pdfs/
```

`data/` is gitignored.
