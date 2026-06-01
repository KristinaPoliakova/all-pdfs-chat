#!/usr/bin/env bash
# Back up the production database (pg_dump -Fc) and the uploads volume.
# Usage: ./backup.sh [label]   (label defaults to "scheduled"; deploy.sh passes "predeploy")
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/all-pdfs-chat}"
COMPOSE="docker compose -f ${APP_DIR}/docker-compose.prod.yml"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/all-pdfs-chat}"
RETAIN_DAYS="${RETAIN_DAYS:-14}"
LABEL="${1:-scheduled}"
ts="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"

echo "[backup] dumping database (${LABEL})..."
dump_file="${BACKUP_DIR}/db-${LABEL}-${ts}.dump"
# Dump to a .partial file and promote on success, so a failed dump never
# leaves a 0-byte file that looks like a valid backup during a restore.
$COMPOSE exec -T postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U all_pdfs_chat -d all_pdfs_chat -Fc' \
  > "${dump_file}.partial"
mv "${dump_file}.partial" "${dump_file}"

echo "[backup] archiving uploads volume..."
docker run --rm \
  -v all-pdfs-chat_uploads:/data:ro \
  -v "${BACKUP_DIR}:/backup" \
  alpine sh -c "tar czf /backup/uploads-${LABEL}-${ts}.tar.gz -C /data ."

echo "[backup] pruning backups older than ${RETAIN_DAYS} days..."
find "$BACKUP_DIR" -type f -mtime +"${RETAIN_DAYS}" -delete

echo "[backup] done: ${dump_file}"
