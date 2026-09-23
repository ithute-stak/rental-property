#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/deploy/.env.production}"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"
ADMIN_EMAIL="${MOSALA_ADMIN_EMAIL:-}"
ADMIN_NAME="${MOSALA_ADMIN_NAME:-Mosala Administrator}"
UPDATE_EXISTING="${MOSALA_ADMIN_UPDATE_EXISTING:-false}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Production environment file not found: $ENV_FILE" >&2
  exit 1
fi
if [[ -z "$ADMIN_EMAIL" ]]; then
  echo "MOSALA_ADMIN_EMAIL is required" >&2
  exit 1
fi
if [[ "$UPDATE_EXISTING" != "true" && "$UPDATE_EXISTING" != "false" ]]; then
  echo "MOSALA_ADMIN_UPDATE_EXISTING must be true or false" >&2
  exit 1
fi

if [[ -z "${MOSALA_ADMIN_PASSWORD:-}" ]]; then
  read -r -s -p "Mosala administrator password: " MOSALA_ADMIN_PASSWORD
  echo
fi
if [[ ${#MOSALA_ADMIN_PASSWORD} -lt 8 ]]; then
  echo "Administrator password must contain at least 8 characters" >&2
  unset MOSALA_ADMIN_PASSWORD
  exit 1
fi

# Export the secret so Compose can pass it by variable name only. This keeps the
# password out of Docker/Compose command-line arguments and shell history.
export MOSALA_ADMIN_PASSWORD

cleanup() {
  unset MOSALA_ADMIN_PASSWORD
}
trap cleanup EXIT

args=(
  python -m app.provision_admin
  --email "$ADMIN_EMAIL"
  --name "$ADMIN_NAME"
)
if [[ "$UPDATE_EXISTING" == "true" ]]; then
  args+=(--update-existing)
fi

# Run inside the production application image. The password exists only in the
# transient process environment and is never written to the repository or env file.
docker compose \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_FILE" \
  run --rm \
  -e MOSALA_ADMIN_PASSWORD \
  api "${args[@]}"
