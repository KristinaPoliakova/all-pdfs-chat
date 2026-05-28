#!/usr/bin/env bash
# Start local dev: PostgreSQL + FastAPI API + background worker + Next.js UI.
# Usage: ./scripts/dev.sh [--setup-only | --stop]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
SETUP_ONLY=false
STOP_ONLY=false
API_PORT=8000
UI_PORT=3000

SERVICE_PIDS=()
PREFIX_PIDS=()
FIFOS=()

for arg in "$@"; do
  case "$arg" in
    --setup-only) SETUP_ONLY=true ;;
    --stop) STOP_ONLY=true ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/dev.sh [options]

  Starts PostgreSQL (Docker Compose), backend API, background worker, and Next.js.
  Press Ctrl+C to stop app processes (PostgreSQL keeps running).

Options:
  --setup-only   Copy env files, start Postgres, install dependencies; do not start app servers
  --stop         Stop orphaned dev servers on ports 8000 and 3000
  -h, --help     Show this help

Prerequisites: PostgreSQL (Docker Compose or local install), uv, Node.js 20+, npm
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)" >&2
      exit 1
      ;;
  esac
done

log() { printf '\033[1;36m[dev]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[dev]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[dev]\033[0m %s\n' "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

# Reads stdin and prints lines prefixed with [tag].
prefix_output() {
  local tag="$1"
  local color="$2"
  while IFS= read -r line || [[ -n "$line" ]]; do
    printf '\033[%sm[%s]\033[0m %s\n' "$color" "$tag" "$line"
  done
}

kill_tree() {
  local pid="$1"
  [[ -z "$pid" ]] && return
  if ! kill -0 "$pid" 2>/dev/null; then
    return
  fi
  local child
  while IFS= read -r child; do
    kill_tree "$child"
  done < <(pgrep -P "$pid" 2>/dev/null || true)
  kill -TERM "$pid" 2>/dev/null || true
}

is_our_dev_process() {
  local cmd="$1"
  case "$cmd" in
    *uvicorn*|*"next dev"*|*next-server*|*"app.worker"*|*"app.main:app"*)
      return 0
      ;;
  esac
  return 1
}

# Stop listeners on dev ports left behind after an incomplete shutdown.
free_dev_ports() {
  local port pid cmd pids
  for port in "$API_PORT" "$UI_PORT"; do
    pids="$(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true)"
    [[ -z "$pids" ]] && continue
    for pid in $pids; do
      cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
      if is_our_dev_process "$cmd"; then
        warn "Stopping leftover process on port ${port} (PID ${pid})…"
        kill_tree "$pid"
      fi
    done
  done
}

ensure_backend_env() {
  if [[ ! -f "$BACKEND/.env" ]]; then
    cp "$BACKEND/.env.example" "$BACKEND/.env"
    log "Created backend/.env from .env.example"
  fi
}

ensure_frontend_env() {
  if [[ ! -f "$FRONTEND/.env.local" ]]; then
    if [[ ! -f "$FRONTEND/.env.local.example" ]]; then
      die "Missing $FRONTEND/.env.local.example"
    fi
    cp "$FRONTEND/.env.local.example" "$FRONTEND/.env.local"
    log "Created frontend/.env.local from .env.local.example"
  fi
}

PG_HOST="${POSTGRES_HOST:-127.0.0.1}"
PG_PORT="${POSTGRES_PORT:-5432}"
PG_USER="${POSTGRES_USER:-all_pdfs_chat}"
PG_DB="${POSTGRES_DB:-all_pdfs_chat}"
PG_TEST_DB="${POSTGRES_TEST_DB:-all_pdfs_chat_test}"

postgres_is_reachable() {
  if command -v pg_isready >/dev/null 2>&1; then
    pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1
    return $?
  fi
  if command -v nc >/dev/null 2>&1; then
    nc -z "$PG_HOST" "$PG_PORT" >/dev/null 2>&1
    return $?
  fi
  return 1
}

die_postgres_not_available() {
  die "PostgreSQL is not available.

Docker was not found, and nothing is listening for user '${PG_USER}' at ${PG_HOST}:${PG_PORT}.

Recommended — Docker (matches docker-compose.yml and backend/.env.example):
  1. Install Docker Desktop: https://docs.docker.com/desktop/install/mac-install/
     (or OrbStack: https://orbstack.dev — lighter on Mac)
  2. Open the app once so the docker CLI works in Terminal
  3. Run: ./scripts/dev.sh

Alternative — Homebrew PostgreSQL (you must create the user/DB yourself):
  brew install postgresql@16
  brew services start postgresql@16
  See scripts/README.md section \"PostgreSQL without Docker\"

After Postgres is up, run: ./scripts/dev.sh"
}

ensure_postgres() {
  if command -v docker >/dev/null 2>&1; then
    ensure_postgres_docker
    return 0
  fi

  if postgres_is_reachable; then
    log "PostgreSQL already reachable at ${PG_HOST}:${PG_PORT} (skipping Docker)."
    ensure_test_database_native
    return 0
  fi

  die_postgres_not_available
}

ensure_postgres_docker() {
  log "Starting PostgreSQL (docker compose)…"
  (cd "$ROOT" && docker compose up -d postgres)
  wait_for_postgres_docker
  ensure_test_database_docker
}

wait_for_postgres_docker() {
  log "Waiting for PostgreSQL to accept connections…"
  local attempt
  for attempt in $(seq 1 30); do
    if (cd "$ROOT" && docker compose exec -T postgres pg_isready -U "$PG_USER" -d "$PG_DB") >/dev/null 2>&1; then
      log "PostgreSQL is ready."
      return 0
    fi
    sleep 1
  done
  die "PostgreSQL did not become ready in time. Check: docker compose logs postgres"
}

ensure_test_database_docker() {
  (cd "$ROOT" && docker compose exec -T postgres psql -U "$PG_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT 'CREATE DATABASE ${PG_TEST_DB}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${PG_TEST_DB}')\gexec
SQL
  ) >/dev/null
}

ensure_test_database_native() {
  if ! command -v psql >/dev/null 2>&1; then
    warn "psql not found — skipping ${PG_TEST_DB} creation (pytest SQL tests may fail)."
    return 0
  fi
  PGPASSWORD="${POSTGRES_PASSWORD:-devpassword}" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL >/dev/null 2>&1 || true
SELECT 'CREATE DATABASE ${PG_TEST_DB}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${PG_TEST_DB}')\gexec
SQL
}

ensure_backend_deps() {
  log "Syncing backend dependencies (uv sync)…"
  (cd "$BACKEND" && uv sync)
}

database_url_for() {
  local db_name="$1"
  printf 'postgresql+asyncpg://%s:%s@%s:%s/%s' \
    "$PG_USER" "${POSTGRES_PASSWORD:-devpassword}" "$PG_HOST" "$PG_PORT" "$db_name"
}

run_database_migrations() {
  local dev_url test_url
  dev_url="$(database_url_for "$PG_DB")"
  test_url="$(database_url_for "$PG_TEST_DB")"
  log "Applying Alembic migrations (dev + test databases)…"
  (cd "$BACKEND" && uv run python -c "
from app.infrastructure.persistence.sql.migrations import ensure_migrated
ensure_migrated('${dev_url}')
ensure_migrated('${test_url}')
")
}

ensure_frontend_deps() {
  if [[ ! -d "$FRONTEND/node_modules" ]]; then
    log "Installing frontend dependencies (npm install)…"
    (cd "$FRONTEND" && npm install)
  else
    log "Frontend node_modules present — skipping npm install"
  fi
}

run_setup() {
  require_cmd uv
  require_cmd node
  require_cmd npm
  ensure_backend_env
  ensure_frontend_env
  ensure_postgres
  ensure_backend_deps
  run_database_migrations
  ensure_frontend_deps
  log "Setup complete."
}

cleanup() {
  log "Stopping dev processes…"
  trap - EXIT INT TERM

  local pid fifo
  for pid in "${SERVICE_PIDS[@]}"; do
    kill_tree "$pid"
  done
  for pid in "${PREFIX_PIDS[@]}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  for fifo in "${FIFOS[@]}"; do
    rm -f "$fifo"
  done

  wait 2>/dev/null || true
  sleep 0.5
  free_dev_ports
}

start_service() {
  local tag="$1"
  local color="$2"
  local dir="$3"
  shift 3

  local fifo
  fifo="$(mktemp -u -t all-pdfs-chat-dev)"
  mkfifo "$fifo"
  FIFOS+=("$fifo")

  prefix_output "$tag" "$color" <"$fifo" &
  PREFIX_PIDS+=("$!")

  (
    cd "$dir"
    exec "$@"
  ) >"$fifo" 2>&1 &
  SERVICE_PIDS+=("$!")
}

run_dev() {
  trap cleanup EXIT INT TERM

  free_dev_ports

  log "Starting API (http://127.0.0.1:${API_PORT})…"
  start_service api 32 "$BACKEND" uv run uvicorn app.main:app --reload --host 127.0.0.1 --port "$API_PORT"

  log "Starting worker…"
  start_service worker 33 "$BACKEND" uv run python -m app.worker

  log "Starting frontend (http://localhost:${UI_PORT})…"
  start_service ui 35 "$FRONTEND" npm run dev -- -p "$UI_PORT"

  log "All services running. Open http://localhost:${UI_PORT} — Ctrl+C to stop."
  wait
}

require_cmd uv
require_cmd node
require_cmd npm
require_cmd lsof

if $STOP_ONLY; then
  free_dev_ports
  log "Done."
  exit 0
fi

run_setup

if $SETUP_ONLY; then
  exit 0
fi

run_dev
