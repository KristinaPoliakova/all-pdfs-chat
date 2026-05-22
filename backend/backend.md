# Backend

Python **3.14**, **`uv`**, async **FastAPI**, **pytest** + **httpx** for API tests.

## Architecture (async upload)

Upload and processing are **split**:

1. **API** — stores PDF bytes + metadata, enqueues one `process_pdf` job, returns **201 immediately** (`processing_status=uploaded`).
2. **Worker** — separate process claims jobs, runs classify → parse, updates the DB.

```
Client  →  POST /api/v1/pdfs  →  API (store + enqueue)  →  201
Client  →  GET /api/v1/pdfs/{id}  ←  DB status (poll)
Worker  →  claim job  →  classify  →  parse  →  update DB
```

**Both processes must run in dev.** 

## Run locally

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload    # terminal 1 — API
uv run python -m app.worker             # terminal 2 — background processing
```

- API docs: http://127.0.0.1:8000/docs  
- Health: `GET /health`, `GET /ready` (readiness for orchestrators)

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/pdfs` | Upload PDF (multipart field `file`). **201** + `Location: /api/v1/pdfs/{id}` |
| `GET` | `/api/v1/pdfs/{id}` | Document metadata + **`processing_status`** |
| `GET` | `/api/v1/pdfs/{id}/pages` | Per-page classification (empty until worker runs) |

**Upload response:** `PdfDocumentResponse` 

## Client / frontend integration

There is **no** server-side “wait until ready” or push (WebSocket/SSE). Progress is **pull-based**:

1. `POST` upload → get `id`.
2. Poll `GET /api/v1/pdfs/{id}` every 1–2s until `processing_status` reaches the state you need.
3. When classified (or later): `GET /api/v1/pdfs/{id}/pages` for page classes.
4. When `parsed`: text extracts are in DB (no GET endpoint yet); safe to enable chat/RAG.

Typical terminal statuses: `classified`, `parsed`, `classification_failed`, `parsing_failed`.

For a future UI: show “Processing…” while status is `uploaded` / `classifying` / `parsing`; enable chat when `parsed`.

## Config

- File: `backend/.env` (template: `.env.example`)
- Code: `app/config/settings.py` → **`get_settings()`** is a cached singleton (`get_settings.cache_clear()` in tests)

| Variable | Notes |
|----------|--------|
| `APP_ENV` | `dev` or `prod` — picks storage + DB backends |
| `DATABASE_URL` | Dev SQLite (default `sqlite+aiosqlite:///./data/app.db`) |
| `AZURE_SQL_CONNECTIONSTRING` | Prod metadata DB (required when `APP_ENV=prod`) |
| `MAX_UPLOAD_SIZE_BYTES` | Default 10 MiB |
| `AZURE_STORAGE_*` | Prod blob storage (required when `APP_ENV=prod`) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins; empty disables CORS |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default `INFO`) |


## `APP_ENV` wiring

| | `dev` | `prod` |
|---|--------|--------|
| PDF bytes | `app/storage/` → disk | Azure Blob |
| Metadata + jobs | `app/metadata/` + `app/jobs/` → SQLite | Azure SQL |

- `create_file_storage()`, `create_pdf_metadata_store()`, and `create_job_queue()` are **singletons** per process.
- **Job queue:** always `SqlJobQueue` in dev/prod (same DB URL as metadata). Tests use `InMemoryJobQueue` via FastAPI overrides in `tests/conftest.py`.
- **Prod SQL driver:** `uv sync --group prod` installs `aioodbc` for `mssql+aioodbc://` URLs.
- **Tests:** in-memory fakes only via `dependency_overrides` — never in `.env`.

## Processing pipeline

**Statuses:** `uploaded` → `classifying` → `classified` → `parsing` → `parsed` (or `classification_failed` / `parsing_failed`)

**Phase 1 — Classify** (when `CLASSIFICATION_ENABLED=true`):
- PyMuPDF + pdfplumber → `pdf_pages` (`born_digital_simple` / `born_digital_complex`)

**Phase 2 — Parse:**
- `born_digital_simple` → local PyMuPDF text extract → `pdf_page_extracts`
- `born_digital_complex` → Azure Document Intelligence (`prebuilt-read`) when `PARSING_ENABLED=true` and endpoint configured

When `PARSING_ENABLED=false`, complex pages are skipped (simple pages still extracted if classified).

`POST /api/v1/pdfs` enqueues a job when `CLASSIFICATION_ENABLED=true`. Upload always returns **201**; failed classification leaves no `pdf_pages` rows.

| Variable | Default | Notes |
|----------|---------|--------|
| `CLASSIFICATION_ENABLED` | `true` | Set `false` to skip enqueue/classification (stays `uploaded`) |
| `CLASSIFICATION_MAX_PAGES` | `500` | Rejects larger PDFs with `classification_failed` |
| `WORKER_POLL_INTERVAL_SECONDS` | `1` | Worker idle poll interval |
| `WORKER_LOCK_TTL_SECONDS` | `300` | Reclaim stale `running` jobs after this many seconds |
| `WORKER_MAX_ATTEMPTS` | `3` | Max job retries before `failed` |
| `PARSING_ENABLED` | `false` | Enable Azure DI for complex pages |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | | Required in prod when `PARSING_ENABLED=true` |
| `AZURE_DOCUMENT_INTELLIGENCE_API_KEY` | | Dev API key; prod uses `DefaultAzureCredential` when empty |
| `PARSING_POLL_INTERVAL_SECONDS` | `2` | Azure DI poll interval |
| `PARSING_MAX_WAIT_SECONDS` | `600` | Azure DI operation timeout |

## Code map

```
app/storage/          FileStorage protocol + local / azure / memory (tests)
app/metadata/           PdfMetadataStore protocol + sql / memory (tests)
app/jobs/               JobQueue protocol + sql / memory (tests)
app/worker/             Worker poll loop + PdfProcessingPipeline
app/parsing/            CompositeDocumentParser + AzureDocumentIntelligenceParser + factory
app/services/pdf_upload.py   validation, size limit, orchestration, enqueue
app/api/deps.py         inject storage + metadata store + job queue
app/api/routes/pdfs.py  POST + GET handlers
app/db/sqlite_paths.py  Resolve absolute SQLite paths, writable check
app/models/             pdf_document, pdf_page, pdf_page_extract, pdf_job
app/classification/     page routing rules (PyMuPDF + pdfplumber features)
```

**Do not reintroduce** `app/repositories/` or route-level `get_db_session` — metadata goes through `PdfMetadataStore`.

## Worker logging

Minimal by design:

- Worker start/stop
- One summary line per PDF: `PDF processed id=… file=… status=… pages=… extracts=… elapsed_ms=…`
- Warnings on classify/parse failure; exception + stack on job failure

Use `LOG_LEVEL=DEBUG` for more detail.

## Startup vs upload

- **Startup:** `init()` on metadata store + job queue creates SQL tables (`data/app.db`).
- **First upload:** creates `data/uploads/pdfs/...` on disk (no prep step for file storage).

After schema changes locally, delete `data/app.db` (and `-wal`/`-shm` if present) and restart **both** API and worker.

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
sqlite3 data/app.db "SELECT id, filename, processing_status FROM pdf_documents;"
sqlite3 data/app.db "SELECT pdf_id, status FROM pdf_jobs;"
ls data/uploads/pdfs/
```

`data/` is gitignored.
