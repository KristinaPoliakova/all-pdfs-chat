# Backend

Python **3.14**, **`uv`**, async **FastAPI**, **pytest** + **httpx** for API tests.

## Project layout

Persistence is split into **five ports**. Each port has a protocol, in-memory test doubles, a factory, and (where applicable) a SQL implementation under `app/db/`.

| Port | Holds | Package | SQL implementation |
|------|-------|---------|-------------------|
| `FileStorage` | Raw PDF bytes | `app/storage/` | — (disk or Azure Blob) |
| `PdfRepository` | Document rows, page classifications, text extracts | `app/pdf_repository/` | `app/db/repositories/pdf.py` → `SqlPdfRepository` |
| `JobQueue` | Background job rows | `app/jobs/` | `app/db/repositories/jobs.py` → `SqlJobQueue` |
| `UserRepository` | User accounts | `app/user_repository/` | `app/db/repositories/users.py` → `SqlUserRepository` |
| `SessionRepository` | Login sessions (token hashes) | `app/session_repository/` | `app/db/repositories/sessions.py` → `SqlSessionRepository` |

```
app/
├── storage/                 # FileStorage — blob bytes (local disk / Azure Blob)
├── pdf_repository/          # PdfRepository port — protocol, InMemoryPdfRepository, factory
├── jobs/                    # JobQueue port — protocol, InMemoryJobQueue, factory
├── user_repository/         # UserRepository port — protocol, InMemoryUserRepository, factory
├── session_repository/      # SessionRepository port — protocol, InMemorySessionRepository, factory
├── auth/                    # AuthService, password/token helpers, get_current_user dep
├── db/                      # Everything SQL-specific
│   ├── base.py              # SQLAlchemy DeclarativeBase
│   ├── engine.py            # Async engine factory
│   ├── database_url.py      # Dev/prod DATABASE_URL resolution
│   ├── azure_sql.py         # Azure connection string → SQLAlchemy URL
│   ├── sqlite_paths.py      # SQLite path helpers
│   ├── runtime.py           # DatabaseRuntime — shared engine + session_factory
│   ├── lifecycle.py         # init_database(), close_database(), get_database()
│   ├── startup_errors.py    # Friendly DB startup error messages
│   ├── models/              # ORM table definitions
│   │   ├── pdf_document.py
│   │   ├── pdf_page.py
│   │   ├── pdf_page_extract.py
│   │   ├── pdf_job.py
│   │   ├── user.py
│   │   └── user_session.py
│   └── repositories/
│       ├── pdf.py           # SqlPdfRepository
│       ├── jobs.py          # SqlJobQueue
│       ├── users.py         # SqlUserRepository
│       └── sessions.py      # SqlSessionRepository
├── api/                     # Routes + FastAPI dependencies
├── services/                # Upload orchestration
├── worker/                  # Job poll loop + processing pipeline
├── parsing/                 # Document parsers (PyMuPDF, Azure DI)
├── classification/          # Page classification rules
├── config/                  # Settings (`get_settings()` singleton)
├── core/                    # Logging, exceptions, shared utils
└── schemas/                 # Pydantic request/response models
```

### How the layers connect

- **API, worker, and services** depend on ports only: `FileStorage`, `PdfRepository`, `JobQueue`, `UserRepository`, `SessionRepository`.
- **Factories** wire dev/prod backends. In tests, FastAPI `dependency_overrides` inject in-memory fakes instead.
- **`AuthService`** (`app/auth/service.py`) orchestrates register/login/logout using both user and session repos. Password hashing and token generation live here, not in repositories.
- **`app/db/`** is the SQL stack. A single **`DatabaseRuntime`** owns the async engine and `async_sessionmaker`; SQL repositories receive the session factory only (no per-repo engines). Nothing outside factories/tests should import SQL repository classes directly.
- **Upload** writes to two backends: bytes → `FileStorage`, document row → `PdfRepository`. The worker reads bytes from storage and writes classification/parsing results to the repository.

Handlers and services do not use raw SQLAlchemy sessions — all SQL access goes through port repositories (`PdfRepository`, `JobQueue`, `UserRepository`, `SessionRepository`).

## Architecture (async upload)

Upload and processing are **split**:

1. **API** — stores PDF bytes + document row, enqueues one `process_pdf` job, returns **201 immediately** (`processing_status=uploaded`).
2. **Worker** — separate process claims jobs, runs classify → parse, updates rows via `PdfRepository`.

```
Client  →  POST /api/v1/pdfs  →  API (FileStorage + PdfRepository + enqueue)  →  201
Client  →  GET /api/v1/pdfs/{id}  ←  PdfRepository (poll status)
Worker  →  claim job  →  classify  →  parse  →  PdfRepository
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
| `POST` | `/api/v1/auth/register` | Create account. **201** + bearer token |
| `POST` | `/api/v1/auth/login` | Sign in. **200** + bearer token |
| `POST` | `/api/v1/auth/logout` | Revoke session (Bearer token). **204** |
| `GET` | `/api/v1/auth/me` | Current user (Bearer token). **200** |
| `POST` | `/api/v1/pdfs` | Upload PDF (multipart field `file`). **201** + `Location: /api/v1/pdfs/{id}` |
| `GET` | `/api/v1/pdfs/{id}` | Document record + **`processing_status`** |
| `GET` | `/api/v1/pdfs/{id}/pages` | Per-page classification (empty until worker runs) |

**Upload response:** `PdfDocumentResponse`

## Client / frontend integration

There is **no** server-side “wait until ready” or push (WebSocket/SSE). Progress is **pull-based**:

1. `POST` upload → get `id`.
2. Poll `GET /api/v1/pdfs/{id}` every 1–2s until `processing_status` reaches the state you need.
3. When classified (or later): `GET /api/v1/pdfs/{id}/pages` for page classes.
4. When `parsed`: text extracts are in the database (no GET endpoint yet); safe to enable chat/RAG.

Typical terminal statuses: `classified`, `parsed`, `classification_failed`, `parsing_failed`.

For a future UI: show “Processing…” while status is `uploaded` / `classifying` / `parsing`; enable chat when `parsed`.

## Config

- File: `backend/.env` (template: `.env.example`)
- Code: `app/config/settings.py` → **`get_settings()`** is a cached singleton (`get_settings.cache_clear()` in tests)

| Variable | Notes |
|----------|--------|
| `APP_ENV` | `dev` or `prod` — picks storage + DB backends |
| `DATABASE_URL` | Dev SQLite (default `sqlite+aiosqlite:///./data/app.db`) |
| `AZURE_SQL_CONNECTIONSTRING` | Prod SQL database (required when `APP_ENV=prod`) |
| `MAX_UPLOAD_SIZE_BYTES` | Default 10 MiB |
| `AZURE_STORAGE_*` | Prod blob storage (required when `APP_ENV=prod`) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins; empty disables CORS |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default `INFO`) |

## `APP_ENV` wiring

| | `dev` | `prod` |
|---|--------|--------|
| PDF bytes (`FileStorage`) | Local disk | Azure Blob |
| PDF rows + jobs + auth (`PdfRepository`, `JobQueue`, `UserRepository`, `SessionRepository`) | SQLite via shared `DatabaseRuntime` | Azure SQL |

- `create_file_storage()`, `create_pdf_repository()`, `create_job_queue()`, `create_user_repository()`, and `create_session_repository()` are **singletons** per process.
- All SQL repositories share one **`DatabaseRuntime`** (one engine, one connection pool) via `get_database()`.
- **Prod SQL driver:** `uv sync --group prod` installs `aioodbc` for `mssql+aioodbc://` URLs.
- **Tests:** in-memory fakes via `dependency_overrides` in `tests/conftest.py` — never configured in `.env`.

## Processing pipeline

**Statuses:** `uploaded` → `classifying` → `classified` → `parsing` → `parsed` (or `classification_failed` / `parsing_failed`)

**Phase 1 — Classify** (when `CLASSIFICATION_ENABLED=true`):
- PyMuPDF + pdfplumber → `pdf_pages` table (`born_digital_simple` / `born_digital_complex`)

**Phase 2 — Parse:**
- `born_digital_simple` → local PyMuPDF text extract → `pdf_page_extracts` table
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
| `SESSION_TTL_SECONDS` | `604800` | Auth session lifetime (7 days) |

## Worker logging

Minimal by design:

- Worker start/stop
- One summary line per PDF: `PDF processed id=… file=… status=… pages=… extracts=… elapsed_ms=…`
- Warnings on classify/parse failure; exception + stack on job failure

Use `LOG_LEVEL=DEBUG` for more detail.

## Startup vs upload

- **Startup:** `init_database()` runs once (API and worker), then port factories wire SQL singletons.
- **First upload:** creates `data/uploads/pdfs/...` on disk (no prep step for file storage).

After local schema changes, delete `data/app.db` (and `-wal`/`-shm` if present) and restart **both** API and worker.

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
