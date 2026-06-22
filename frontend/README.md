# All PDFs Chat — Frontend POC

Next.js App Router UI for uploading a PDF, polling processing status, and chatting once parsing completes.

## Prerequisites

- Node.js 20+
- Backend API and worker running locally (see below) when **not** using mocked APIs

## Environment

Copy the example env file and adjust if your API runs on a different host:

```bash
cp .env.local.example .env.local
```

| Variable | Purpose |
|----------|---------|
| `BACKEND_URL` | FastAPI origin for Next.js rewrites (default `http://127.0.0.1:8000`) |
| `NEXT_PUBLIC_API_BASE` | Browser fetch prefix (default `/api/v1`) |
| `NEXT_PUBLIC_MAX_UPLOAD_BYTES` | Client-side upload size cap (default 10 MiB) |

Requests from the browser go to `/api/v1/*` on the Next dev server; `next.config.ts` rewrites those paths to `BACKEND_URL`.

## Authentication

The backend requires a **Bearer token** on all PDF endpoints. The frontend uses **lazy auth**:

1. The upload page is visible without signing in
2. Upload or document fetch returns **401** → inline prompt with Sign in / Register links
3. After login, users return to where they were (`?returnTo=...`)
4. Header shows Sign in / Register when logged out; email + Sign out when logged in

## Local development

**One terminal (recommended):**

```bash
./scripts/dev.sh
```

Setup only (env files + dependencies, no servers):

```bash
./scripts/dev.sh --setup-only
```

See [scripts/README.md](../scripts/README.md) for details.

**Manual (three terminals):**

```bash
# Terminal 1 — API
cd backend && uv run uvicorn app.main:app --reload

# Terminal 2 — Worker (required or status stays at uploaded)
cd backend && uv run python -m app.worker

# Terminal 3 — Frontend
cd frontend && cp .env.local.example .env.local && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Chat

Chat calls the backend endpoint `POST /pdfs/{id}/chat` via `src/lib/api/chat.ts`. When `processing_status` is `parsed`, the chat panel unlocks and assistant replies (with optional page citations) come from the assistant. Errors are surfaced inline via `chatErrorMessage` in `src/lib/api/errors.ts`.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Next.js dev server (port 3000) |
| `npm run build` | Production build |
| `npm test` | Vitest unit tests |
| `npx playwright test` | E2E tests (mocked `/api/v1/pdfs` — no backend required) |

### E2E without backend

Playwright tests intercept `/api/v1/auth/me` and `/api/v1/pdfs` routes in the test file itself, seeding a mock bearer token in `localStorage`, so CI and local E2E runs do not need the API or worker:

```bash
npx playwright install chromium   # first time only
npx playwright test
```

## Project layout

- `src/app/` — routes (`/` upload, `/login`, `/register`, `/pdfs/[id]` status + chat)
- `src/lib/api/` — typed fetch helpers (auth + PDFs)
- `src/lib/auth/` — token session storage
- `src/contexts/` — `AuthProvider`
- `tests/unit/` — Vitest + Testing Library
- `tests/e2e/` — Playwright (mocked API)
