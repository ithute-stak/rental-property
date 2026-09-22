# Mosala Rental Property Marketplace

A location-aware rental marketplace and occupancy-management platform for Mosala Advertising and Marketing Agency, developed by Ithute Digital Solutions.

The product follows the full rental lifecycle:

`discover -> verify -> advertise -> book -> occupy -> give notice -> re-advertise -> vacate -> inspect -> occupy again`

## Stack

- Flutter + BLoC mobile application
- FastAPI REST API
- PostgreSQL + PostGIS
- Alembic migrations
- Redis booking holds and maintenance locking
- S3-compatible object storage for property media
- background maintenance worker
- WebSocket/push delivery remains a later real-time integration slice

## Repository layout

```text
backend/     FastAPI API, workers, models, migrations and tests
mobile/      Flutter client
docs/        architecture, roadmap and production runbooks
```

## Local backend

```bash
cp .env.example .env
make infra-up
make api-install
make migrate
make api-run
```

FastAPI is available at `http://localhost:8000`; process liveness is `GET /api/v1/health/live`, dependency readiness is `GET /api/v1/health/ready`, and the legacy `GET /api/v1/health` endpoint remains available. OpenAPI is at `/docs`.

For the complete local infrastructure, including MinIO, migrations and the maintenance worker:

```bash
docker compose up -d
```

## Production baseline

A separate production Compose baseline keeps PostgreSQL and Redis off public host ports and binds FastAPI only to `127.0.0.1:8000` for an HTTPS reverse proxy:

```bash
cp .env.production.example .env.production
# Replace every placeholder before continuing.
docker compose --env-file .env.production -f docker-compose.production.yml config
docker compose --env-file .env.production -f docker-compose.production.yml build
```

See `docs/PRODUCTION_DEPLOYMENT.md` before deploying. It covers secrets, database backups, migrations, health verification, administrator provisioning, monitoring and rollback expectations.

## Provision the first Mosala administrator

Public registration deliberately allows only house-seeker and landlord accounts. Create the initial administrator from a trusted server shell after migrations have run:

```bash
cd backend
mosala-provision-admin --phone YOUR_ADMIN_PHONE --name "Mosala Administrator"
```

The command securely prompts for the password without requiring it on the command line. An email can be supplied with `--email`. If a matching account already exists, the command refuses to change it unless `--update-existing` is supplied deliberately.

With the development Compose backend image, the same command can be run through the migration service:

```bash
docker compose run --rm migrate mosala-provision-admin \
  --phone YOUR_ADMIN_PHONE \
  --name "Mosala Administrator"
```

Do not commit production credentials to this repository. When `APP_ENV=production`, the API refuses to start with the development JWT or object-storage secret defaults.

## Flutter

If platform runners are not yet present on a workstation with Flutter installed, generate them once and then run the application:

```bash
cd mobile
flutter create --platforms=android,ios,web .
flutter pub get
flutter run
```

Do not regenerate `lib/` when adding platform runners.

## Implemented marketplace capabilities

- JWT authentication and role-based access control
- landlord profile verification and Mosala admin review
- property/rental-unit separation and lifecycle management
- property media upload, gallery and cover-image management
- PostGIS radius search, rent/location filters and trigram typo-tolerant text search
- Redis-backed booking holds and database protection against competing active bookings
- booking payment-reference review and internal double-entry-style funds ledger
- tenancy activation, future vacancy, notice-to-vacate, move-out and inspection lifecycle
- automatic re-advertising of units that are vacating soon
- advertising charge quote/payment/waiver/activation lifecycle
- Saved Homes and property viewing requests
- private property-scoped messaging with unread/read state
- in-app event notifications
- admin marketplace analytics and landlord portfolio analytics
- automatic unpaid-booking expiry and upcoming-viewing reminders
- production-safe worker locking and production-secret validation
- separate liveness/readiness health probes for production orchestration

## Validation

CI validates both development and production Compose configuration, compiles the backend, applies the complete Alembic migration chain to PostgreSQL/PostGIS, runs backend tests, builds the backend Docker image, runs Flutter analysis and executes Flutter tests.

Live payment-provider settlement and external push/WebSocket delivery are intentionally not simulated; those are integration slices that require the selected production providers and credentials.

See `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/PRODUCTION_DEPLOYMENT.md` for the wider system design and operational guidance.
