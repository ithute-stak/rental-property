#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/deploy/.env.production}"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT_DIR/backups}"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"
MC_IMAGE="minio/mc:RELEASE.2025-04-16T18-13-26Z"
NETWORK_NAME="mosala-rentals_default"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Production environment file not found: $ENV_FILE" >&2
  exit 1
fi

umask 077
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$BACKUP_ROOT/$TIMESTAMP"
MEDIA_STAGE="$DEST/media-stage"
mkdir -p "$MEDIA_STAGE"

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Backing up PostgreSQL to $DEST/postgres.dump"
compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DEST/postgres.dump"

echo "Mirroring MinIO bucket to a private staging directory"
docker run --rm \
  --network "$NETWORK_NAME" \
  --env-file "$ENV_FILE" \
  -v "$MEDIA_STAGE:/backup" \
  --entrypoint /bin/sh \
  "$MC_IMAGE" \
  -c '
    until mc alias set source http://minio:9000 "$OBJECT_STORAGE_ACCESS_KEY" "$OBJECT_STORAGE_SECRET_KEY" >/dev/null 2>&1; do
      sleep 2
    done
    mc mirror --overwrite source/"$OBJECT_STORAGE_BUCKET" /backup
  '

tar -czf "$DEST/media.tar.gz" -C "$MEDIA_STAGE" .
rm -rf "$MEDIA_STAGE"

GIT_COMMIT="$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || printf unknown)"
{
  echo "created_at=$TIMESTAMP"
  echo "git_commit=$GIT_COMMIT"
  echo "database_format=pg_dump_custom"
  echo "media_format=tar_gzip_from_s3_mirror"
} > "$DEST/manifest.txt"

(
  cd "$DEST"
  sha256sum postgres.dump media.tar.gz manifest.txt > SHA256SUMS
)

ln -sfn "$TIMESTAMP" "$BACKUP_ROOT/latest"
echo "Backup complete: $DEST"
