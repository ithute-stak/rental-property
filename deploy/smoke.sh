#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/deploy/.env.production}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Production environment file not found: $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${API_DOMAIN:?API_DOMAIN must be set in the production environment file}"
BASE_URL="https://${API_DOMAIN}/api/v1"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

request() {
  local path="$1"
  local body_file="$2"
  local headers_file="$3"
  curl --fail --silent --show-error \
    --connect-timeout 10 \
    --max-time 30 \
    -D "$headers_file" \
    -o "$body_file" \
    "${BASE_URL}${path}"
}

echo "Checking Mosala Rentals at ${BASE_URL}"

request "/health/live" "$TMP_DIR/live.json" "$TMP_DIR/live.headers"
grep -q '"status":"ok"' "$TMP_DIR/live.json"
grep -qi '^strict-transport-security:' "$TMP_DIR/live.headers"
grep -qi '^x-request-id:' "$TMP_DIR/live.headers"
echo "  liveness/TLS/request-id: OK"

request "/health/ready" "$TMP_DIR/ready.json" "$TMP_DIR/ready.headers"
grep -q '"status":"ready"' "$TMP_DIR/ready.json"
grep -q '"database":"ok"' "$TMP_DIR/ready.json"
grep -q '"redis":"ok"' "$TMP_DIR/ready.json"
echo "  database/Redis readiness: OK"

request "/properties/feed?limit=1" "$TMP_DIR/feed.json" "$TMP_DIR/feed.headers"
grep -q '^\[' "$TMP_DIR/feed.json"
echo "  public property feed: OK"

AUTH_STATUS="$(curl --silent --show-error \
  --connect-timeout 10 \
  --max-time 30 \
  -o "$TMP_DIR/auth.json" \
  -w '%{http_code}' \
  "${BASE_URL}/auth/me")"
if [[ "$AUTH_STATUS" != "401" ]]; then
  echo "Expected /auth/me without a token to return 401, got ${AUTH_STATUS}" >&2
  exit 1
fi
echo "  unauthenticated access control: OK"

echo "Production smoke checks passed."
