# Mosala Rentals Production Deployment Runbook

This runbook describes a conservative single-VPS deployment for the Mosala Rental Property Marketplace. It deliberately keeps PostgreSQL and Redis private to Docker, binds FastAPI only to the VPS loopback interface, and assumes TLS/reverse-proxy termination is managed on the host or by an existing platform proxy.

## 1. Server prerequisites

Install Docker Engine with the Docker Compose plugin. Create a dedicated non-root deployment user with permission to run Docker. Keep the repository, environment file and database backups readable only by the deployment/operations account.

The production host should expose only the ports needed by the reverse proxy, normally 80 and 443. PostgreSQL 5432 and Redis 6379 must not be exposed publicly.

## 2. Production environment

Copy the template and replace every placeholder:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Generate independent strong credentials for PostgreSQL, Redis, JWT signing and object storage. URL-encode database or Redis passwords when embedding them in `DATABASE_URL` or `REDIS_URL`.

`APP_ENV=production` activates startup protection that refuses known development secrets. `CORS_ORIGINS` must contain only the HTTPS origins that are allowed to make credentialed browser requests.

Property media in production should use a real S3-compatible object-storage endpoint reachable by the mobile application. The development MinIO service is intentionally not part of `docker-compose.production.yml`.

## 3. Validate before deployment

```bash
docker compose --env-file .env.production -f docker-compose.production.yml config >/dev/null
docker compose --env-file .env.production -f docker-compose.production.yml build
```

Do not continue if either command fails.

## 4. Database backup before every upgrade

Create a backup directory outside the repository and restrict its permissions. Before applying migrations:

```bash
mkdir -p backups
chmod 700 backups
set -a
. ./.env.production
set +a

docker compose --env-file .env.production -f docker-compose.production.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  > "backups/mosala-$(date +%Y%m%d-%H%M%S).dump"
```

Copy backups off the VPS as well. A backup that exists only on the same server is not sufficient disaster recovery.

Periodically test restoration into a separate PostgreSQL instance. Do not wait for an incident to discover that a backup cannot be restored.

## 5. Deploy or upgrade

```bash
git pull --ff-only

docker compose --env-file .env.production -f docker-compose.production.yml build

docker compose --env-file .env.production -f docker-compose.production.yml run --rm migrate

docker compose --env-file .env.production -f docker-compose.production.yml up -d api worker
```

The migration command must complete successfully before the API or worker is replaced.

## 6. Health verification

The application provides two health contracts:

- `GET /api/v1/health/live` — confirms the FastAPI process is running.
- `GET /api/v1/health/ready` — confirms the process can reach both PostgreSQL and Redis.

The production API container healthcheck uses the readiness endpoint. After deployment:

```bash
curl --fail http://127.0.0.1:8000/api/v1/health/live
curl --fail http://127.0.0.1:8000/api/v1/health/ready

docker compose --env-file .env.production -f docker-compose.production.yml ps
```

A reverse proxy should send public API traffic only to `127.0.0.1:8000` and should terminate HTTPS. Do not publish the API directly to the internet without TLS.

## 7. First administrator

After migrations are complete, provision the initial Mosala administrator from the server shell:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml run --rm migrate \
  mosala-provision-admin --phone YOUR_ADMIN_PHONE --name "Mosala Administrator"
```

The command prompts for the password securely. Do not put the administrator password in shell history, Compose YAML, GitHub Actions, or repository files.

## 8. Operational checks

Monitor at minimum:

- API readiness and HTTP 5xx rate;
- PostgreSQL disk usage, connection count and backup age;
- Redis availability and memory usage;
- worker logs and maintenance-cycle failures;
- VPS disk, RAM, CPU and inode utilization;
- TLS certificate expiry;
- object-storage reachability and upload failures.

Set external uptime monitoring against the HTTPS readiness route only if exposing dependency status publicly is acceptable. Otherwise monitor a lightweight public endpoint and check readiness from the host/private monitoring network.

## 9. Rollback strategy

Application rollback and database rollback are separate decisions. If a release fails before migrations, redeploy the previous application commit/image. If migrations have already changed schema, do not blindly run Alembic downgrade in production. Review the migration and restore from the pre-deployment backup when data-destructive reversal would be unsafe.

Keep the previous known-good Git commit or image reference available until the new release has passed smoke tests.

## 10. Release acceptance checklist

Before declaring a release complete, verify sign-in, landlord property submission, admin review, public search, media loading, booking hold/creation, payment-reference submission, admin payment confirmation, tenancy activation, messaging, notifications, and the background maintenance worker against production-like infrastructure.

Live payment-provider and push-notification credentials should be introduced only after their adapters are implemented and tested; they should remain external secrets, never repository content.
