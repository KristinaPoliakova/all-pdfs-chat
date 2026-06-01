#!/usr/bin/env bash
# Production deploy: pull tagged images, back up DB, migrate, (re)start, health-check.
# Usage: IMAGE_TAG=v1.2.3 ./deploy.sh   (run from the app dir on the droplet)
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/all-pdfs-chat}"
COMPOSE="docker compose -f ${APP_DIR}/docker-compose.prod.yml"
ENV_FILE="${APP_DIR}/.env"
IMAGE_TAG="${IMAGE_TAG:-latest}"

cd "$APP_DIR"
echo "[deploy] deploying IMAGE_TAG=${IMAGE_TAG}"

# Persist IMAGE_TAG for compose interpolation, preserving other vars (e.g. POSTGRES_PASSWORD).
touch "$ENV_FILE"
if grep -q '^IMAGE_TAG=' "$ENV_FILE"; then
  sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=${IMAGE_TAG}|" "$ENV_FILE"
else
  echo "IMAGE_TAG=${IMAGE_TAG}" >> "$ENV_FILE"
fi

echo "[deploy] pulling images..."
$COMPOSE pull api worker frontend

echo "[deploy] ensuring postgres is up..."
$COMPOSE up -d postgres
pg_ok=0
for _ in $(seq 1 30); do
  if $COMPOSE exec -T postgres pg_isready -U all_pdfs_chat -d all_pdfs_chat >/dev/null 2>&1; then
    pg_ok=1; break
  fi
  sleep 2
done
if [ "$pg_ok" -ne 1 ]; then
  echo "[deploy] postgres did not become ready in time" >&2
  exit 1
fi

echo "[deploy] backing up database before migration..."
"${APP_DIR}/deploy/backup.sh" predeploy

echo "[deploy] running migrations (alembic upgrade head)..."
$COMPOSE run --rm api alembic upgrade head

echo "[deploy] starting/refreshing services..."
$COMPOSE up -d

# nginx resolves upstream (api/frontend) hostnames at start and caches the IPs.
# Recreating api/frontend above gives them new IPs, so nginx must be recreated
# to re-resolve them — otherwise it serves 502s on /api/v1 after each deploy.
echo "[deploy] recreating nginx to re-resolve upstream IPs..."
$COMPOSE up -d --force-recreate --no-deps nginx

echo "[deploy] health check (api /ready)..."
ok=0
for _ in $(seq 1 30); do
  if $COMPOSE exec -T api python -c \
      "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/ready').status==200 else 1)" \
      >/dev/null 2>&1; then
    ok=1; break
  fi
  sleep 2
done
if [ "$ok" -ne 1 ]; then
  echo "[deploy] HEALTH CHECK FAILED — services not ready" >&2
  $COMPOSE ps
  exit 1
fi

echo "[deploy] pruning dangling images..."
docker image prune -f >/dev/null || true
echo "[deploy] SUCCESS (IMAGE_TAG=${IMAGE_TAG})"
