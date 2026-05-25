#!/usr/bin/env bash
# Start local dev: FastAPI API + background worker + Next.js UI in one terminal.
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

  Starts the backend API, background worker, and Next.js dev server together.
  Press Ctrl+C to stop all processes.

Options:
  --setup-only   Copy env files and install dependencies; do not start servers
  --stop         Stop orphaned dev servers on ports 8000 and 3000
  -h, --help     Show this help

Prerequisites: uv (https://docs.astral.sh/uv/), Node.js 20+, npm
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

ensure_backend_deps() {
  log "Syncing backend dependencies (uv sync)…"
  (cd "$BACKEND" && uv sync)
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
  ensure_backend_deps
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
