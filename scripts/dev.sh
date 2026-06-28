#!/usr/bin/env bash
# Start local dev: PostgreSQL + MLflow + FastAPI API + background worker + Next.js UI.
# Usage: ./scripts/dev.sh [--setup-only | --stop]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
SETUP_ONLY=false
STOP_ONLY=false
DOCKER_MODE=false
API_PORT=8000
UI_PORT=3000
DEV_COMPOSE="docker-compose.dev.yml"
MONITORING_COMPOSE="docker-compose.monitoring.yml"
DEV_DOCKER_PORT=8080
GRAFANA_PORT=3001

SERVICE_PIDS=()
PREFIX_PIDS=()
FIFOS=()

for arg in "$@"; do
  case "$arg" in
    --setup-only) SETUP_ONLY=true ;;
    --stop) STOP_ONLY=true ;;
    --docker) DOCKER_MODE=true ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/dev.sh [options]

  Default (native): starts PostgreSQL and the MLflow tracking server (Docker
  Compose) plus the backend API, background worker, and Next.js as local
  processes with hot reload.
  Press Ctrl+C to stop app processes (PostgreSQL and MLflow keep running).

Options:
  --setup-only   Copy env files, start Postgres + MLflow, install dependencies; do not start app servers
  --stop         Stop orphaned dev servers on ports 8000 and 3000
  --docker       Run the FULL stack in containers (api, worker, frontend, nginx, postgres)
                 from docker-compose.dev.yml — a high-fidelity mirror of production
                 (incl. nginx routing) for a pre-release smoke test. Serves
                 http://localhost:8080. Also starts the observability stack
                 (docker-compose.monitoring.yml): Prometheus + Grafana at
                 http://localhost:3001 (node-exporter is skipped — Linux-only).
                 No hot reload — use the native mode for daily work.
  --docker --stop  Tear the containerized dev stack + monitoring down (docker compose down)
  -h, --help     Show this help

Prerequisites: native mode needs PostgreSQL (Docker), uv, Node.js 20+, npm.
               --docker mode needs only Docker.
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

# --- Containerized full-stack dev (docker-compose.dev.yml) -------------------
# Layers the observability stack (docker-compose.monitoring.yml) on top, so the
# containerized dev mirror also runs Prometheus + Grafana. node-exporter is
# skipped locally: its host-mount propagation (/:/host:ro,rslave) is rejected by
# Docker Desktop on macOS and yields no real host metrics there — it runs only on
# the Linux droplet in production.
run_docker_dev() {
  require_cmd docker
  local compose=(docker compose -f "$DEV_COMPOSE" -f "$MONITORING_COMPOSE")
  log "Building images (first run can take a few minutes)…"
  (cd "$ROOT" && "${compose[@]}" build)
  log "Starting PostgreSQL…"
  (cd "$ROOT" && "${compose[@]}" up -d postgres)
  log "Ensuring MLflow database (${MLFLOW_DB}) exists…"
  (cd "$ROOT" && "${compose[@]}" exec -T postgres psql -U "$PG_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT 'CREATE DATABASE ${MLFLOW_DB}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${MLFLOW_DB}')\gexec
SQL
  ) >/dev/null
  log "Applying database migrations…"
  (cd "$ROOT" && "${compose[@]}" run --rm api alembic upgrade head)
  log "Starting full stack + monitoring (api, worker, frontend, nginx, mlflow, prometheus, grafana)…"
  (cd "$ROOT" && "${compose[@]}" up -d --scale node-exporter=0)
  log "Full-stack dev running at http://localhost:${DEV_DOCKER_PORT}  (API via nginx: http://localhost:${DEV_DOCKER_PORT}/api/v1)"
  log "MLflow UI at http://localhost:${MLFLOW_PORT}  (tracing is ON in this mirror)"
  log "Grafana at http://localhost:${GRAFANA_PORT}  (login admin/admin; Host dashboard is empty locally — node-exporter is Linux-only)"
  log "Logs:  docker compose -f ${DEV_COMPOSE} -f ${MONITORING_COMPOSE} logs -f"
  log "Stop:  ./scripts/dev.sh --docker --stop"
}

stop_docker_dev() {
  require_cmd docker
  log "Stopping containerized dev stack (incl. monitoring)…"
  (cd "$ROOT" && docker compose -f "$DEV_COMPOSE" -f "$MONITORING_COMPOSE" down)
  log "Done."
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
# Host port for the MLflow UI. Defaults to 5001 because macOS' AirPlay Receiver
# squats on 5000 and answers with HTTP 403. Exported so docker-compose.yml's
# ${MLFLOW_HOST_PORT} mapping matches the URL we print and suggest.
MLFLOW_DB="${MLFLOW_DB:-mlflow}"
MLFLOW_PORT="${MLFLOW_HOST_PORT:-${MLFLOW_PORT:-5001}}"
export MLFLOW_HOST_PORT="$MLFLOW_PORT"

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

# MLflow tracking server (self-hosted, reuses the Postgres container). Only the
# Docker path is supported — the server runs from the docker-compose.yml `mlflow`
# service. Tracing itself stays opt-in: the app emits traces only when
# TRACING_ENABLED=true (set it, plus MLFLOW_TRACKING_URI, in backend/.env).
ensure_mlflow() {
  if ! command -v docker >/dev/null 2>&1; then
    warn "Docker not found — skipping MLflow tracking server (tracing will be unavailable)."
    return 0
  fi
  ensure_mlflow_database_docker
  log "Starting MLflow tracking server (docker compose; first run builds the image)…"
  (cd "$ROOT" && docker compose up -d mlflow)
  wait_for_mlflow
  log "MLflow UI: http://localhost:${MLFLOW_PORT}  (enable tracing via TRACING_ENABLED=true + MLFLOW_TRACKING_URI=http://localhost:${MLFLOW_PORT} in backend/.env)"
}

# Wait until MLflow answers /health so the API (which configures tracing at
# startup) doesn't race a container that accepts connections before its workers
# are ready. Best-effort: tracing is opt-in, so warn rather than die on timeout.
wait_for_mlflow() {
  command -v curl >/dev/null 2>&1 || return 0
  log "Waiting for MLflow to accept connections…"
  local attempt
  for attempt in $(seq 1 30); do
    if curl -fsS -o /dev/null --max-time 2 "http://localhost:${MLFLOW_PORT}/health"; then
      log "MLflow is ready."
      return 0
    fi
    sleep 1
  done
  warn "MLflow did not become ready in time; request/agent tracing may be disabled this run."
}

ensure_mlflow_database_docker() {
  (cd "$ROOT" && docker compose exec -T postgres psql -U "$PG_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT 'CREATE DATABASE ${MLFLOW_DB}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${MLFLOW_DB}')\gexec
SQL
  ) >/dev/null
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
  ensure_mlflow
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

if $DOCKER_MODE; then
  if $STOP_ONLY; then
    stop_docker_dev
  else
    run_docker_dev
  fi
  exit 0
fi

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
