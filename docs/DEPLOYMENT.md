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

Set the real API/media domains, TLS email, browser CORS origins and storage public URL. `OBJECT_STORAGE_PUBLIC_BASE_URL` should normally be `https://<MEDIA_DOMAIN>/<OBJECT_STORAGE_BUCKET>`.

## 3. Validate before starting

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml config >/dev/null
bash -n deploy/backup.sh deploy/restore.sh
```

## 4. Start the platform

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml build
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d
```

The one-shot `migrate` service runs Alembic before the API/worker start. MinIO initialization creates the configured media bucket and enables public object download for listing images.

Verify readiness through the public API domain:

```bash
curl -fsS https://YOUR_API_DOMAIN/api/v1/health/ready
```

Expected result reports `status=ready`, database OK and Redis OK.

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

The mobile app accepts the API base URL at build time:

```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=https://YOUR_API_DOMAIN/api/v1
```

Use the equivalent `flutter build appbundle`, `flutter build ios`, or web build command for the target release channel. The realtime client derives `wss://` from the same production API base URL.

## 7. Routine deployment/update

Before each update, create a backup. Then update the repository and rebuild:

```bash
bash deploy/backup.sh
git pull --ff-only origin main
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml build
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d
curl -fsS https://YOUR_API_DOMAIN/api/v1/health/ready
```

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

Always verify readiness and a representative landlord/property/booking workflow after restoration before reopening normal use.

## 10. Operational checks

Useful commands:

```bash
# Service status
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps

# API logs
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs -f api

# Worker/realtime relay logs
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs -f worker

# Reverse proxy / TLS logs
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs -f caddy
```

Monitor disk space, backup age, PostgreSQL volume growth, API readiness and certificate renewal. Redis contains transient locks/pub-sub state and is not treated as the durable source of marketplace records.

## 11. Rollback principle

Application rollback and data rollback are different operations. If a new container build is faulty but migrations are backward compatible, deploy the previous application commit without restoring data. Only restore a database/media backup when the stored business data itself must be rolled back, because restoring a backup discards newer transactions.
