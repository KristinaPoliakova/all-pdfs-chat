# Scripts

## Local development

Run API, worker, and Next.js from a single terminal:

```bash
chmod +x scripts/dev.sh   # first time only
./scripts/dev.sh
```

The script will:

1. Create `backend/.env` and `frontend/.env.local` from examples if missing
2. Run `uv sync` in `backend/`
3. Run `npm install` in `frontend/` if `node_modules` is absent
4. Start all three processes with prefixed logs (`[api]`, `[worker]`, `[ui]`)

Press **Ctrl+C** to stop everything (API, worker, UI, and uvicorn/Next child processes).

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

**Requires:** [uv](https://docs.astral.sh/uv/), Node.js 20+, npm.
