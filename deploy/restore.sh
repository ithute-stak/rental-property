#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/deploy/.env.production}"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"
MC_IMAGE="minio/mc:RELEASE.2025-04-16T18-13-26Z"
NETWORK_NAME="mosala-rentals_default"
BACKUP_DIR="${1:-$ROOT_DIR/backups/latest}"
START_APPLICATION_SERVICES="${START_APPLICATION_SERVICES:-true}"

if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Refusing restore. Re-run with CONFIRM_RESTORE=YES after verifying the backup and maintenance window." >&2
  exit 1
fi
if [[ "$START_APPLICATION_SERVICES" != "true" && "$START_APPLICATION_SERVICES" != "false" ]]; then
  echo "START_APPLICATION_SERVICES must be true or false" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Production environment file not found: $ENV_FILE" >&2
  exit 1
fi
if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi
for file in postgres.dump media.tar.gz manifest.txt SHA256SUMS; do
  if [[ ! -f "$BACKUP_DIR/$file" ]]; then
    echo "Backup is incomplete; missing $file" >&2
    exit 1
  fi
done

(
  cd "$BACKUP_DIR"
  sha256sum -c SHA256SUMS
)

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Stopping application writers before restore"
compose stop api worker caddy || true
compose up -d db redis minio minio-init

for _ in $(seq 1 60); do
  if compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
if ! compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
  echo "PostgreSQL did not become ready" >&2
  exit 1
fi

echo "Restoring PostgreSQL"
cat "$BACKUP_DIR/postgres.dump" | compose exec -T db sh -c '
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges
'

MEDIA_STAGE="$(mktemp -d)"
trap 'rm -rf "$MEDIA_STAGE"' EXIT
tar -xzf "$BACKUP_DIR/media.tar.gz" -C "$MEDIA_STAGE"

echo "Restoring object storage bucket"
docker run --rm \
  --network "$NETWORK_NAME" \
  --env-file "$ENV_FILE" \
  -v "$MEDIA_STAGE:/backup:ro" \
  --entrypoint /bin/sh \
  "$MC_IMAGE" \
  -c '
    until mc alias set target http://minio:9000 "$OBJECT_STORAGE_ACCESS_KEY" "$OBJECT_STORAGE_SECRET_KEY" >/dev/null 2>&1; do
      sleep 2
    done
    mc mb --ignore-existing target/"$OBJECT_STORAGE_BUCKET" >/dev/null
    mc mirror --overwrite --remove /backup target/"$OBJECT_STORAGE_BUCKET"
  '

echo "Applying any migrations newer than the backup"
compose run --rm migrate

if [[ "$START_APPLICATION_SERVICES" == "true" ]]; then
  echo "Starting application services"
  compose up -d api worker caddy
  echo "Restore completed. Verify the public /api/v1/health/ready endpoint before reopening traffic."
else
  echo "Restore completed with application services intentionally left stopped."
fi
