# Scripts

## Environment files

| File | Use when |
|------|----------|
| `backend/.env.example` | **Local development.** `./scripts/dev.sh` copies this to `backend/.env` if missing. PostgreSQL (Docker Compose) + local disk uploads. |
| `backend/.env.production.example` | **Production VM** (e.g. DigitalOcean droplet). Reference only — copy to `/etc/all-pdfs-chat/backend.env`, fill in secrets, and load from systemd. PostgreSQL + local storage. |
| `frontend/.env.local.example` | **Local frontend.** Copied to `frontend/.env.local` by `dev.sh` if missing. |

Do not commit `backend/.env`, `frontend/.env.local`, or server env files with real credentials. **Do** commit `*.example` templates — they contain placeholders only.

## Local development

Run PostgreSQL, API, worker, and Next.js from a single terminal:

```bash
chmod +x scripts/dev.sh   # first time only
./scripts/dev.sh
```

The script will:

1. Create `backend/.env` and `frontend/.env.local` from examples if missing
2. Start PostgreSQL via `docker compose up -d postgres` and wait until ready
3. Ensure the `all_pdfs_chat_test` database exists (for pytest)
4. Run `uv sync` in `backend/`
5. Run `npm install` in `frontend/` if `node_modules` is absent
6. Start all three app processes with prefixed logs (`[api]`, `[worker]`, `[ui]`)

Press **Ctrl+C** to stop app processes. PostgreSQL keeps running in Docker until you stop it:

```bash
docker compose stop postgres
# or wipe dev Postgres data (Docker named volume postgres_data):
docker compose down -v
```

If a previous run left ports busy, either run again (the script stops matching listeners on 8000/3000 before start) or:

```bash
./scripts/dev.sh --stop
```

### Setup without starting servers

```bash
./scripts/dev.sh --setup-only
```

### URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API docs | http://127.0.0.1:8000/docs |
| API health | http://127.0.0.1:8000/health |

**Requires:** PostgreSQL, [uv](https://docs.astral.sh/uv/), Node.js 20+, npm. PostgreSQL is usually started via Docker (see below).

### PostgreSQL with Docker (recommended)

Install one of:

- [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- [OrbStack](https://orbstack.dev) (Docker-compatible, often faster on Mac)

Open the app once, then confirm the CLI works:

```bash
docker --version
docker compose version
```

`./scripts/dev.sh` runs `docker compose up -d postgres` automatically.

### PostgreSQL without Docker

If you already run Postgres on `127.0.0.1:5432`, `dev.sh` skips Docker when it can connect with the credentials in `backend/.env.example`.

With Homebrew you must create the role and database yourself (example):

```bash
brew install postgresql@16
brew services start postgresql@16

# As a superuser (often your macOS user via local socket):
createuser -s all_pdfs_chat 2>/dev/null || true
psql -d postgres -c "ALTER USER all_pdfs_chat WITH PASSWORD 'devpassword';"
createdb -O all_pdfs_chat all_pdfs_chat
createdb -O all_pdfs_chat all_pdfs_chat_test
```

Keep `DATABASE_URL` in `backend/.env` aligned with your setup.

### Running tests

Most API tests use in-memory fakes and do not require PostgreSQL. SQL integration tests (`test_*_sql.py` and SQL-backed cases in other modules) connect to **`all_pdfs_chat_test`**, created automatically by `dev.sh` or `deploy/postgres/init/01-create-test-db.sql` on first Docker Postgres start.

Each SQL test opens the test database via `open_test_database()`, which runs `create_all` then **truncates all app tables** so tests do not leak state.

```bash
./scripts/dev.sh --setup-only
cd backend && uv run pytest -q
```

Override the test URL if needed:

```bash
export TEST_DATABASE_URL='postgresql+asyncpg://user:pass@127.0.0.1:5432/all_pdfs_chat_test'
cd backend && uv run pytest -q tests/test_pdf_jobs_sql.py
```
