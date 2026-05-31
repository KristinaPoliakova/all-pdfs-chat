# CI Pipeline — Design Spec

- **Date:** 2026-05-31
- **Status:** Approved (design) — pending implementation plan
- **Scope:** Continuous Integration only. Continuous Deployment is explicitly deferred.

## 1. Context & current state

`all-pdfs-chat` is a monorepo with three runtime pieces:

- **Backend API** — Python 3.14, `uv`, async FastAPI (`app.main:app`).
- **Background worker** — separate process (`python -m app.worker`), same codebase.
- **Frontend** — Next.js 16 / React 19 / TypeScript.
- **Datastore** — PostgreSQL (SQLAlchemy + asyncpg, Alembic migrations).

Quality tooling already present:

| Area | Tools |
|------|-------|
| Backend lint/format | `ruff` (lint + format) |
| Backend types | `mypy` (strict) |
| Backend tests | `pytest`, `pytest-asyncio`, `pytest-cov` |
| Frontend lint | ESLint (`eslint-config-next`) |
| Frontend unit tests | Vitest (`tests/unit`) |
| Frontend E2E | Playwright (`tests/e2e`) — CI-aware config exists |
| Pre-commit | ruff lint + format on `backend/**/*.py` only |

There is **no CI today**. Blocking issues and gaps:

1. **`.github` is a stray 0-byte file**, which prevents creating a `.github/workflows/` directory.
2. No automated pipeline of any kind.
3. Pre-commit covers backend ruff only; frontend has no local hook.
4. No `Dockerfile`s for the app (only a `docker-compose.yml` that runs Postgres for dev).
5. Frontend has no dedicated `typecheck` script.

### Hard constraints discovered in code

- Backend tests **hardcode** the database connection (they do not read it from an env var):
  - `backend/tests/conftest.py` and `backend/tests/settings_helpers.py` →
    `postgresql+asyncpg://all_pdfs_chat:devpassword@127.0.0.1:5432/all_pdfs_chat_test`
  - **Implication:** the CI Postgres service must use user `all_pdfs_chat`, password `devpassword`, port `5432`, and the `all_pdfs_chat_test` database must exist. No test-code changes are required if CI matches these values.
- SQL integration tests run real Alembic migrations against the test DB (`ensure_migrated`) and truncate app tables for isolation.
- Secrets hygiene is already correct: `.gitignore` ignores all `.env*` except `*.example`.

## 2. Goals & non-goals

### Goals
- Automated CI on **GitHub Actions** that, on every push, validates both backend and frontend.
- Add production-ready **Dockerfiles** for API/worker and frontend; CI **builds them to validate** (no registry push, no deploy).
- Strengthen **local git hooks** as the first line of defense for a solo developer (no PR review step exists).
- Follow CI best practices: least-privilege permissions, dependency caching, run cancellation, fast feedback via path filtering.

### Non-goals (deferred)
- **No Continuous Deployment.** No image push, no release, no server provisioning.
- **No Playwright/E2E in CI.** E2E stays local for now.
- No branch-protection / required-status-check configuration (solo dev, no PRs).

## 3. Decisions (from brainstorming)

| Decision | Choice |
|----------|--------|
| Platform | GitHub Actions |
| Scope | CI only; CD deferred |
| Containerization | Add Dockerfiles now (API + worker + frontend); build-validate in CI, do **not** push |
| E2E in CI | No — unit + integration only |
| Triggers | `push` to **all branches** + manual `workflow_dispatch` |
| Local hooks | Add a **`pre-push`** hook (fast checks) **and** extend pre-commit to cover frontend (ESLint) |
| Infra | Greenfield — CD designed later |

## 4. Architecture

A single workflow file `.github/workflows/ci.yml`. Because there are no PRs/branch protection, there is **no aggregator gate job**. Path filtering is used purely to keep runs fast.

```
push (any branch) / workflow_dispatch
        │
        ▼
   ┌─────────┐
   │ changes │  dorny/paths-filter → outputs: backend, frontend, docker
   └────┬────┘
        ├───────────────┬────────────────┐
        ▼               ▼                ▼
   ┌─────────┐    ┌──────────┐    ┌──────────────┐
   │ backend │    │ frontend │    │ docker-build │
   │  (if    │    │  (if     │    │  (if docker  │
   │ backend)│    │ frontend)│    │  or code)    │
   └─────────┘    └──────────┘    └──────────────┘
```

Each job runs independently; failures are visible per job on the commit status.

### 4.1 `changes` job
- `dorny/paths-filter` with filters:
  - `backend`: `backend/**`
  - `frontend`: `frontend/**`
  - `docker`: `backend/**`, `frontend/**`, `**/Dockerfile`, `docker-compose.yml`, `.dockerignore`
- Emits boolean outputs consumed by downstream `if:` conditions.

### 4.2 `backend` job
Runs when `changes.outputs.backend == 'true'`.

- Runner: `ubuntu-latest`.
- **Postgres service container**: image `postgres:16.6-alpine`, env `POSTGRES_USER=all_pdfs_chat`, `POSTGRES_PASSWORD=devpassword`, `POSTGRES_DB=all_pdfs_chat`, port `5432:5432`, with a `pg_isready` health check.
- Steps:
  1. `actions/checkout`.
  2. `astral-sh/setup-uv` (enable cache) → install **Python 3.14** + `uv sync` (working dir `backend/`).
  3. Create the test DB: `psql .../postgres -c "CREATE DATABASE all_pdfs_chat_test"` (idempotent guard).
  4. `uv run ruff check .` (no `--fix`).
  5. `uv run ruff format --check .`.
  6. `uv run mypy app`.
  7. `uv run alembic upgrade head` (against the test DB; matches `backend.md`'s documented CI step).
  8. `uv run pytest -q --cov=app` (runs in-memory + SQL integration tests).
- Caching: uv cache via the setup action.

### 4.3 `frontend` job
Runs when `changes.outputs.frontend == 'true'`.

- Runner: `ubuntu-latest`.
- Steps:
  1. `actions/checkout`.
  2. `actions/setup-node` (Node 20, `cache: npm`, `cache-dependency-path: frontend/package-lock.json`).
  3. `npm ci` (working dir `frontend/`).
  4. `npm run lint`.
  5. `npm run typecheck` (**new script**, see §6).
  6. `npm run test` (Vitest).
  7. `npm run build` (`next build`).

### 4.4 `docker-build` job
Runs when `changes.outputs.docker == 'true'`.

- Uses `docker/setup-buildx-action` + `docker/build-push-action` with `push: false` and GHA layer cache (`cache-from`/`cache-to: type=gha`).
- Builds the two images to prove the Dockerfiles are valid:
  - **backend** (one image; the worker reuses it with a different command).
  - **frontend**.
- No registry authentication, no push, no artifacts retained.

### 4.5 Workflow-level hygiene
- `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }` — supersede stale runs on the same ref.
- `permissions: { contents: read }` — least privilege.
- Triggers: `on: { push: {}, workflow_dispatch: {} }` (all branches).

## 5. New Dockerfiles

- **`backend/Dockerfile`** — multi-stage, `uv`-based, Python 3.14 slim base. Installs deps from `uv.lock` (locked, reproducible), copies `app/` + `alembic/`. Default `CMD` runs the API via `uvicorn app.main:app`. The **worker** uses the same image with command `python -m app.worker` (set by the future orchestrator/compose). Non-root user.
- **`frontend/Dockerfile`** — multi-stage Node 20 build → Next.js **standalone** runtime image. Requires adding `output: 'standalone'` to `next.config.ts` (see §6). Non-root user.
- **`backend/.dockerignore`** and **`frontend/.dockerignore`** — exclude `.venv`, `node_modules`, `.next`, caches, `data/`, env files.

These Dockerfiles are validated by CI now and become the foundation for the deferred CD phase.

## 6. Repository preparation / modifications

| Change | File | Why |
|--------|------|-----|
| Delete stray file | `.github` (0-byte file) | Blocks `.github/workflows/` |
| Add CI workflow | `.github/workflows/ci.yml` | The pipeline |
| Add typecheck script | `frontend/package.json` → `"typecheck": "tsc --noEmit"` | CI/type gate; currently missing |
| Enable standalone output | `frontend/next.config.ts` → `output: 'standalone'` | Lean frontend Docker image |
| Backend image | `backend/Dockerfile`, `backend/.dockerignore` | Containerize API + worker |
| Frontend image | `frontend/Dockerfile`, `frontend/.dockerignore` | Containerize frontend |
| Extend pre-commit | `.pre-commit-config.yaml` | Frontend ESLint hook + pre-push stage |

## 7. Local git hooks (solo-dev safety net)

Since there is no PR review, local hooks are the primary pre-`main` gate.

- **pre-commit (commit stage)** — keep existing backend ruff hooks; **add** a frontend ESLint hook (a `repo: local` hook running `npm run lint` scoped to `frontend/**` changes).
- **pre-push (push stage)** — a `repo: local` hook set that runs **fast** checks before a push reaches GitHub:
  - backend: `ruff check`, `ruff format --check`, `mypy app`
  - frontend: `npm run lint`, `npm run typecheck`, `npm run test`
  - Rationale for "fast": full backend `pytest` SQL integration requires a running Postgres; that remains a CI responsibility. (Whether to also attempt `pytest` on pre-push when Postgres is up is an open option for the plan — see §10.)
- Install command documented: `pre-commit install --hook-type pre-commit --hook-type pre-push`.

## 8. File inventory (created / modified)

**Created**
- `.github/workflows/ci.yml`
- `backend/Dockerfile`, `backend/.dockerignore`
- `frontend/Dockerfile`, `frontend/.dockerignore`

**Modified**
- `.github` (deleted as a file; recreated as a directory)
- `frontend/package.json` (add `typecheck` script)
- `frontend/next.config.ts` (add `output: 'standalone'`)
- `.pre-commit-config.yaml` (frontend ESLint + pre-push stage)
- Docs: `scripts/README.md` / `backend.md` updated to reference CI + hook install (minor).

## 9. Verification plan

- **Backend job:** push a branch; confirm ruff/format/mypy/alembic/pytest all run green against the Postgres service; intentionally break a lint rule to confirm the job fails.
- **Frontend job:** confirm lint/typecheck/vitest/build run green; break a type to confirm failure.
- **Docker job:** confirm all images build with `push: false`.
- **Path filtering:** a docs-only commit triggers neither backend nor frontend jobs (only `changes`); a `backend/**` change runs backend (+docker) but not frontend.
- **Local hooks:** `git push` with a lint error is blocked locally; a clean tree passes.

## 10. Open options for the implementation plan

1. **pre-push depth:** static-only (default) vs. also run `pytest` when a local Postgres is detected.
2. **Coverage threshold:** report-only vs. enforce a `--cov-fail-under` minimum.
3. **Doc updates scope:** how much of `backend.md` / `scripts/README.md` to touch.

## 11. Deferred: Continuous Deployment (future phase, not built now)

Recommended direction once ready (greenfield): **build & push images to GHCR on tagged releases, then deploy containers** (the Dockerfiles added here are the foundation). Alternatives — SSH + systemd to a DigitalOcean droplet (matches current `.env.production.example` docs) or a PaaS — will be evaluated in a dedicated CD design.
