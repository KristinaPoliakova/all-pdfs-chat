# Backend

Python **3.14**, **`uv`**, async **FastAPI**, **pytest** + **httpx** for API tests.

## Project layout

Persistence is split into **five ports** (application layer). Each port has a protocol under `app/application/ports/`, in-memory test doubles under `app/infrastructure/persistence/memory/`, a factory under `app/infrastructure/factories/`, and (where applicable) a SQL implementation under `app/infrastructure/persistence/sql/`.

| Port | Holds | Protocol | SQL implementation |
|------|-------|----------|-------------------|
| `FileStorage` | Raw PDF bytes | `application/ports/storage.py` | — (disk or Azure Blob under `infrastructure/storage/`) |
| `PdfRepository` | Document rows, page classifications, text extracts | `application/ports/pdf.py` | `infrastructure/persistence/sql/repositories/pdf.py` → `SqlPdfRepository` |
| `JobQueue` | Background job rows | `application/ports/jobs.py` | `infrastructure/persistence/sql/repositories/jobs.py` → `SqlJobQueue` |
| `UserRepository` | User accounts | `application/ports/users.py` | `infrastructure/persistence/sql/repositories/users.py` → `SqlUserRepository` |
| `SessionRepository` | Login sessions (token hashes) | `application/ports/sessions.py` | `infrastructure/persistence/sql/repositories/sessions.py` → `SqlSessionRepository` |

```
app/
├── api/                     # HTTP delivery — routes + FastAPI dependencies
├── worker/                  # Background delivery — job poll loop + pipeline
│
├── application/             # Use cases + port definitions (no infrastructure imports)
│   ├── auth/                # AuthService, password/token helpers, get_current_user dep
│   ├── services/            # Upload orchestration
│   └── ports/
│       ├── pdf.py           # PdfRepository, PdfRecord
│       ├── users.py         # UserRepository, UserRecord
│       ├── sessions.py      # SessionRepository, SessionRecord
│       ├── jobs.py          # JobQueue, PdfJobRecord, JobStatus
│       └── storage.py       # FileStorage
│
├── infrastructure/          # Concrete backends (SQL, blob, in-memory fakes)
│   ├── persistence/
│   │   ├── sql/             # SQLAlchemy stack
│   │   │   ├── base.py
│   │   │   ├── runtime.py   # DatabaseRuntime — shared engine + session_factory
│   │   │   ├── lifecycle.py # get_database(), init/close, URL from DATABASE_URL
│   │   │   ├── startup_errors.py
│   │   │   ├── models/      # ORM table definitions
│   │   │   └── repositories/  # SqlPdfRepository, SqlJobQueue, …
│   │   └── memory/          # InMemory* test doubles
│   ├── storage/             # LocalFileStorage, AzureBlobStorage, InMemoryFileStorage
│   └── factories/           # create_* wiring for dev/prod singletons
│
├── parsing/                 # Document parsers (PyMuPDF, Azure DI)
├── classification/          # Page classification rules
├── config/                  # Settings (`get_settings()` singleton)
├── core/                    # Logging, exceptions, shared utils
└── schemas/                 # Pydantic request/response models
```

### How the layers connect

- **API and worker** depend on ports and application services only — never on SQL or storage implementations directly.
- **`application/`** defines ports and use cases. It must not import from `infrastructure/`.
- **Factories** (`infrastructure/factories/`) wire dev/prod backends. In tests, FastAPI `dependency_overrides` inject in-memory fakes instead.
- **`AuthService`** (`app/application/auth/service.py`) orchestrates register/login/logout using both user and session repos. Password hashing and token generation live here, not in repositories.
- **`infrastructure/persistence/sql/`** is the SQL stack. A single **`DatabaseRuntime`** owns the async engine and `async_sessionmaker`; SQL repositories receive the session factory only (no per-repo engines). Nothing outside factories/tests should import SQL repository classes directly.
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

From the repo root, start API + worker + frontend together:

```bash
./scripts/dev.sh
```

Or run backend processes manually (PostgreSQL must be up — see repo-root `docker compose up -d postgres`):

```bash
docker compose up -d postgres
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload    # terminal 1 — API
uv run python -m app.worker             # terminal 2 — background processing
```

- API docs: http://127.0.0.1:8000/docs
- Health: `GET /health` (liveness), `GET /ready` (readiness — app started and `SELECT 1` against PostgreSQL when the DB was initialized at startup)

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/auth/register` | Create account. **201** + bearer token |
| `POST` | `/api/v1/auth/login` | Sign in. **200** + bearer token |
| `POST` | `/api/v1/auth/logout` | Revoke session (Bearer token). **204** |
| `GET` | `/api/v1/auth/me` | Current user (Bearer token). **200** |
| `POST` | `/api/v1/pdfs` | Upload PDF (multipart field `file`, **Bearer token required**). **201** + `Location: /api/v1/pdfs/{id}` |
| `GET` | `/api/v1/pdfs/{id}` | Document record + **`processing_status`** (**Bearer token**, owner only) |
| `GET` | `/api/v1/pdfs/{id}/pages` | Per-page classification (**Bearer token**, owner only) |
| `POST` | `/api/v1/pdfs/{id}/chat` | Ask a question about a parsed PDF (Bearer token, owner only). **200** + `{answer, citations}`; **409** until parsed |

**Upload response:** `PdfDocumentResponse`

## Client / frontend integration

There is **no** server-side “wait until ready” or push (WebSocket/SSE). Progress is **pull-based**:

1. Register/login → obtain bearer token.
2. `POST` upload with `Authorization: Bearer <token>` → get `id`.
3. Poll `GET /api/v1/pdfs/{id}` every 1–2s until `processing_status` reaches the state you need.
4. When classified (or later): `GET /api/v1/pdfs/{id}/pages` for page classes.
5. When `parsed`: text extracts are in the database (no GET endpoint yet); safe to enable chat/RAG.

Once `processing_status == parsed`, the client can `POST /api/v1/pdfs/{id}/chat` with `{"message": "..."}` and receives `{"answer", "citations": [page numbers]}`. See [Agent (chat)](#agent-chat).

Typical terminal statuses: `classified`, `parsed`, `classification_failed`, `parsing_failed`.

For a future UI: show “Processing…” while status is `uploaded` / `classifying` / `parsing`; enable chat when `parsed`.

## Config

**Deployment:** see `docs/deployment.md` (Docker Compose on a VM).

- File: `backend/.env` (template: `.env.example`)
- Code: `app/config/settings.py` → **`get_settings()`** is a cached singleton (`get_settings.cache_clear()` in tests)

| Variable | Notes |
|----------|--------|
| `APP_ENV` | `dev` or `prod` — picks storage + DB backends |
| `DATABASE_URL` | PostgreSQL async URL (`postgresql+asyncpg://…`); dev default matches `docker-compose.yml` |
| `STORAGE_BACKEND` | `local` (default) or `azure` when `APP_ENV=prod` |
| `LOCAL_STORAGE_PATH` | Override upload directory (default `backend/data/uploads`) |
| `MAX_UPLOAD_SIZE_BYTES` | Default 10 MiB |
| `AZURE_STORAGE_*` | Required when `APP_ENV=prod` and `STORAGE_BACKEND=azure` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins; empty disables CORS |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default `INFO`) |
| `RATE_LIMIT_*` | Per-route slowapi limits; active only when `APP_ENV=prod` and `RATE_LIMIT_ENABLED=true` (see `app/core/rate_limit.py`) |

**Rate limiting:** In production, nginx applies a coarse per-IP floor on `/api/v1/` (`limit_req` in `deploy/nginx/conf.d/app.conf`). The API enforces stricter limits via slowapi: auth routes by client IP (`X-Forwarded-For` / `X-Real-IP`), PDF routes by user ID from the bearer session. Returns HTTP 429 with `Retry-After`. Disabled entirely in `dev`.

## `APP_ENV` wiring

| | `dev` | `prod` |
|---|--------|--------|
| PDF bytes (`FileStorage`) | Local disk | Local disk or Azure Blob (`STORAGE_BACKEND`) |
| PDF rows + jobs + auth | PostgreSQL via shared `DatabaseRuntime` | PostgreSQL via shared `DatabaseRuntime` |

- Local PostgreSQL: `docker compose up -d postgres` (started automatically by `./scripts/dev.sh`).
- `create_file_storage()`, `create_pdf_repository()`, `create_job_queue()`, `create_user_repository()`, and `create_session_repository()` are **singletons** per process.
- All SQL repositories share one **`DatabaseRuntime`** (one engine, one connection pool) via `get_database()`.
- **SQL driver:** `asyncpg` via `postgresql+asyncpg://` URLs (`uv sync` installs it).
- **Tests:** most API tests use in-memory fakes via `dependency_overrides` in `tests/conftest.py`. SQL repository tests use PostgreSQL database `all_pdfs_chat_test` (see `tests/settings_helpers.py`); each test run applies Alembic migrations via `open_test_database()` then **truncates all app tables** for isolation.

## Database migrations (Alembic)

Schema changes are **version-controlled** and applied with [Alembic](https://alembic.sqlalchemy.org/) — not `create_all` at startup.

| Command (from `backend/`) | Purpose |
|---------------------------|---------|
| `uv run alembic upgrade head` | Apply pending migrations |
| `uv run alembic current` | Show applied revision |
| `uv run alembic revision --autogenerate -m "…"` | Draft migration from model changes (**review before commit**) |
| `uv run alembic downgrade -1` | Roll back one revision (staging drills) |
| `uv run alembic stamp head` | Mark DB current without DDL (legacy `create_all` DBs only) |

**Local workflow:** `./scripts/dev.sh` (or `--setup-only`) starts Postgres, runs `uv sync`, then migrates **both** `all_pdfs_chat` and `all_pdfs_chat_test`.

**Startup:** `init_database()` verifies connectivity and checks the DB is at Alembic head. In **prod** a stale schema fails startup; in **dev** a warning is logged. Run migrations **before** restarting API and worker after model changes.

**CI:** `.github/workflows/ci.yml` runs `uv run alembic upgrade head` then `uv run pytest -q --cov=app` against a Postgres 16.6 service container (DB `all_pdfs_chat_test`, creds matching `tests/`).

### Production migration rules

| Rule | Why |
|------|-----|
| Never edit a migration already applied to prod | History is immutable — add a new revision |
| One logical change per revision | Easier review and rollback |
| Always ship a working `downgrade()` | Staging rollback drills |
| Destructive changes = two phases | expand → deploy → contract (rename/drop columns) |
| Run migrations before process restart | Avoid old code on new schema or vice versa |
| `pg_dump -Fc` before prod upgrade | Mandatory once client-facing |
| Review autogen output in PR | Autogen is a draft, not truth |

More detail: `backend/alembic/README`.

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
| `CLASSIFICATION_MAX_PAGES` | `10` | Rejects larger PDFs with `classification_failed` |
| `WORKER_POLL_INTERVAL_SECONDS` | `1` | Worker idle poll interval |
| `WORKER_LOCK_TTL_SECONDS` | `300` | Reclaim stale `running` jobs after this many seconds |
| `WORKER_MAX_ATTEMPTS` | `3` | Max job retries before `failed` |
| `PARSING_ENABLED` | `false` | Enable Azure DI for complex pages |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | | Required in prod when `PARSING_ENABLED=true` |
| `AZURE_DOCUMENT_INTELLIGENCE_API_KEY` | | Dev API key; prod uses `DefaultAzureCredential` when empty |
| `PARSING_POLL_INTERVAL_SECONDS` | `2` | Azure DI poll interval |
| `PARSING_MAX_WAIT_SECONDS` | `600` | Azure DI operation timeout |
| `SESSION_TTL_SECONDS` | `604800` | Auth session lifetime (7 days) |

### Worker concurrency

**Decision:** one PDF per worker process, sequential pipeline steps, no in-job page parallelism. Scale throughput with **more worker replicas** (`python -m app.worker`), not `create_task` / multiple jobs in one process. Target **~1 active classify job per core** (reduce if memory-bound).

| Approach | Optimizes | Status |
|----------|-----------|--------|
| Sequential worker (claim → full `pipeline.run` → complete) | Simplicity, predictable memory | **Current** |
| Multiple worker processes/containers (same or extra VMs) | PDFs/hour (throughput) | **Preferred scale-up** |
| In-job page batches (`ProcessPoolExecutor`) | One large PDF latency | **Deferred** (#9) |
| Multiple `pipeline.run` tasks on one event loop | Throughput in one process | **Not planned** |

Inside one job: `await` steps run in order (classify all pages, then parse). `asyncio.to_thread` offloads PyMuPDF/download from the event loop; it does not parallelize pages or jobs.

## Agent (chat)

`POST /api/v1/pdfs/{id}/chat` (Bearer token, owner only) answers questions about a parsed PDF. Body `{"message": "..."}`; returns `{"answer": "...", "citations": [page numbers]}`.

| Status | Meaning |
|--------|---------|
| `200` | Answer produced + page-number citations |
| `404` | PDF not found, or not owned by the caller |
| `409` | PDF not yet `parsed` (no text to ground answers in) |
| `422` | Empty or oversized `message` |
| `502` | Model/runtime unavailable (e.g. Ollama not reachable) |
| `504` | Agent exceeded `AGENT_TIMEOUT_SECONDS` |

**How it works:** a hand-built LangGraph `StateGraph` runs a tool-calling loop (model ↔ tools) grounded in the parsed page text (`pdf_page_extracts`). Two retrieval tools are exposed to the model:

- `search_pages` — find the most relevant pages for a query (top `AGENT_SEARCH_TOP_K`).
- `get_page` — fetch the full text of a specific page.

Answers cite the page numbers used, returned as `citations`.

**Model (Ollama):** the model runs locally on [Ollama](https://ollama.com/) (free) and **must support tool calling** (e.g. `llama3.1`). To run it:

```bash
# install Ollama (see ollama.com), then:
ollama pull llama3.1
# ensure it serves at OLLAMA_BASE_URL (default http://localhost:11434)
```

**Conversation memory:** persisted by LangGraph's `AsyncPostgresSaver` in the `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, and `checkpoint_migrations` tables. These are created at startup via the saver's `setup()` and are **excluded from Alembic autogenerate** (so Alembic never tries to drop them — see `alembic/env.py`). `thread_id = pdf_id`, so each PDF has its own conversation thread.

| Variable | Default | Notes |
|----------|---------|--------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1` | Must support tool calling |
| `AGENT_SEARCH_TOP_K` | `4` | Pages returned by `search_pages` |
| `AGENT_MAX_TOOL_ITERATIONS` | `5` | Max model ↔ tool loops per request |
| `AGENT_TIMEOUT_SECONDS` | `60` | Per-request agent timeout (→ `504`) |
| `AGENT_TOOL_CHAR_LIMIT` | `6000` | Max characters returned by a single tool call |

## Worker logging

Minimal by design:

- Worker start/stop
- One summary line per PDF: `PDF processed id=… file=… status=… pages=… extracts=… elapsed_ms=…`
- Warnings on classify/parse failure; exception + stack on job failure

Use `LOG_LEVEL=DEBUG` for more detail.

## Startup vs upload

- **Startup:** `init_database()` verifies DB connectivity and Alembic head revision, then port factories wire SQL singletons.
- **First upload:** creates `data/uploads/pdfs/...` on disk (no prep step for file storage).

After schema/model changes: `uv run alembic upgrade head`, then restart **both** API and worker. Reset dev data with `docker compose down -v` if needed.

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

PostgreSQL must be running before SQL integration tests (including `test_*_sql.py` and SQL sections in other tests):

```bash
# from repo root — starts Postgres, syncs deps, runs Alembic on dev + test DBs
./scripts/dev.sh --setup-only
cd backend && uv run pytest -q
```

Or run the full suite:

```bash
uv run pytest -q
uv run ruff check app tests
uv run mypy app
```

```bash
docker compose exec postgres psql -U all_pdfs_chat -d all_pdfs_chat \
  -c "SELECT id, filename, processing_status FROM pdf_documents;"
docker compose exec postgres psql -U all_pdfs_chat -d all_pdfs_chat \
  -c "SELECT pdf_document_id, status FROM pdf_jobs;"
ls data/uploads/pdfs/
```

`data/` is gitignored.
