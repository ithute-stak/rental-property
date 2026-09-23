# Mosala Rentals production deployment

This guide deploys the FastAPI API, PostgreSQL/PostGIS, Redis, MinIO, maintenance/realtime worker and Caddy TLS proxy on one Linux VPS. PostgreSQL, Redis and MinIO are not published directly to the host network; only Caddy exposes ports 80/443.

## 1. VPS prerequisites

Install Docker Engine with the Compose plugin and Git. Allow inbound TCP 80/443 and UDP 443. Keep SSH restricted to trusted administration sources where possible.

Recommended DNS records before deployment:

- `API_DOMAIN` -> VPS public IP
- `MEDIA_DOMAIN` -> VPS public IP

Caddy obtains and renews TLS certificates automatically once DNS resolves and ports 80/443 are reachable.

## 2. Create production secrets

Copy the template and never commit the resulting file:

```bash
cp deploy/.env.production.example deploy/.env.production
chmod 600 deploy/.env.production
```

Generate URL-safe secrets so they can be used safely inside connection URLs:

```bash
openssl rand -hex 32   # PostgreSQL password
openssl rand -hex 32   # Redis password
openssl rand -hex 48   # AUTH_SECRET_KEY
openssl rand -hex 32   # MinIO secret
```

Use different generated values for PostgreSQL, Redis, authentication and object storage. Set the real API/media domains, TLS email, browser CORS origins and storage public URL. `OBJECT_STORAGE_PUBLIC_BASE_URL` should normally be `https://<MEDIA_DOMAIN>/<OBJECT_STORAGE_BUCKET>`.

Set `APP_VERSION` to the human release version and `RELEASE_SHA` to the exact full 40-character Git commit deployed. The liveness endpoint exposes both values so an operator can immediately confirm which build is serving traffic.

## 3. Validate before starting

Production deployment is fail-closed. Run:

```bash
make prod-validate
```

The validation target first runs `tools/production_preflight.py`. It rejects placeholder/example domains, local or reserved hostnames, invalid release identity, non-HTTPS public URLs/CORS origins, weak or reused production secrets, mismatched media storage URLs and malformed production values. It then validates Docker Compose and deployment-script syntax.

The checked-in `deploy/.env.production.example` is documentation only and is intentionally expected to fail production preflight until every placeholder has been replaced in `deploy/.env.production`.

CI tests both successful and rejected preflight cases and also validates the Caddyfile with the same Caddy image used in production.

## 4. Start the platform

```bash
make prod-up
```

`prod-up` depends on `prod-validate`, so the production stack cannot be started through the supported Make target without passing preflight first. The one-shot `migrate` service runs Alembic before the API/worker start. MinIO initialization creates the configured media bucket and enables public object download for listing images.

Verify liveness and readiness through the public API domain:

```bash
curl -fsS https://YOUR_API_DOMAIN/api/v1/health/live
curl -fsS https://YOUR_API_DOMAIN/api/v1/health/ready
```

The liveness result includes the configured application version and release commit. Readiness reports database and Redis availability.

## 5. Provision the first Mosala administrator

Run this only from the trusted VPS shell:

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml \
  run --rm migrate mosala-provision-admin \
  --phone YOUR_ADMIN_PHONE \
  --name "Mosala Administrator"
```

The command prompts for the password rather than exposing it in shell history.

## 6. Build the Flutter client against production

The supported Android production path is the protected **Android Production Release** GitHub Actions workflow. It requires the protected production API base URL, Google Maps key, Android upload keystore/signing credentials and, when publishing, the Google Play service-account credential.

Before Java/Flutter build setup begins, the workflow runs the same production preflight rules. It rejects placeholder or reserved API hosts, malformed/non-production Google Maps keys, missing signing secrets, the wrong Android application ID, invalid versions and malformed Google Play service-account JSON. Production Android releases are locked to `ls.co.mosala.rentals`.

For local development or non-production smoke builds, the mobile app still accepts the API base URL at build time:

```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=https://YOUR_API_DOMAIN/api/v1
```

Do not treat a locally built bundle as the Play production candidate unless it came through the protected signed release workflow. The realtime client derives `wss://` from the same production API base URL.

## 7. Routine deployment/update

Before each update, create a backup. Then update the repository and rebuild:

```bash
bash deploy/backup.sh
git pull --ff-only origin main
```

Update `RELEASE_SHA` in `deploy/.env.production` to the output of `git rev-parse HEAD`, update `APP_VERSION` when the release version changes, then continue:

```bash
make prod-up
bash deploy/smoke.sh
```

Because `make prod-up` always runs `prod-validate` first, a stale placeholder, malformed production URL, weak/reused secret or invalid release identity stops the update before containers are rebuilt.

The smoke script verifies HTTPS liveness, dependency readiness, request-ID propagation, HSTS, the public property feed, and unauthenticated access control on `/auth/me`.

Do not run destructive Docker cleanup commands against named Mosala volumes.

## 8. Backups

Run:

```bash
bash deploy/backup.sh
```

Each timestamped backup contains:

- PostgreSQL custom-format dump (`postgres.dump`)
- MinIO bucket mirror archived as `media.tar.gz`
- deployment manifest
- SHA-256 checksums

The database dump is logically consistent. Media is copied through the S3 API rather than by copying the live MinIO filesystem. For the strongest point-in-time consistency, schedule backups during a low-write maintenance window.

`backups/latest` points to the newest local backup. Local backups are not sufficient disaster recovery: copy completed backup directories to encrypted off-VPS storage and test restores periodically.

A typical cron job can invoke the script nightly, followed by your approved encrypted/off-site transfer mechanism.

## 9. Restore

A restore is intentionally guarded because it replaces database/media state. Choose the backup and enter a maintenance window:

```bash
CONFIRM_RESTORE=YES bash deploy/restore.sh backups/20260922T120000Z
```

The script verifies checksums, stops API/worker writers, restores PostgreSQL and the MinIO bucket, applies newer Alembic migrations if required, then starts the application again.

Always run `bash deploy/smoke.sh` and verify a representative landlord/property/booking workflow after restoration before reopening normal use.

## 10. Operational checks

Useful commands:

```bash
# Service status
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps

# API logs (request IDs, method/path, response status and duration; no request bodies/tokens)
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs -f api

# Worker/realtime relay logs
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs -f worker

# Reverse proxy / TLS JSON access logs
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs -f caddy
```

Monitor disk space, backup age, PostgreSQL volume growth, API readiness and certificate renewal. Redis contains transient locks/pub-sub state and is not treated as the durable source of marketplace records.

Every HTTP response carries `X-Request-ID`. Use it to correlate a user-visible failure with the API request log. The API also adds baseline browser security headers; Caddy remains responsible for HSTS because it terminates TLS.

## 11. Rollback principle

Application rollback and data rollback are different operations. If a new container build is faulty but migrations are backward compatible, deploy the previous application commit without restoring data. Only restore a database/media backup when the stored business data itself must be rolled back, because restoring a backup discards newer transactions.
