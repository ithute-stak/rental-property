# Mosala Rental Property Marketplace

A location-aware rental marketplace and occupancy-management platform for Mosala Advertising and Marketing Agency, developed by Ithute Digital Solutions.

The product follows the full rental lifecycle:

`discover -> verify -> advertise -> book -> occupy -> give notice -> re-advertise -> vacate -> inspect -> occupy again`

## Stack

- Flutter + BLoC mobile application
- FastAPI REST + WebSocket API
- PostgreSQL + PostGIS
- Alembic migrations
- Redis booking holds, worker locks and realtime Pub/Sub
- S3-compatible object storage for property media
- background maintenance and realtime notification worker
- Caddy reverse proxy with automatic production TLS

## Repository layout

```text
backend/                 FastAPI API, workers, models, migrations and tests
mobile/                  Flutter client
docs/                    architecture, roadmap and deployment operations
deploy/                  production proxy, environment template and recovery scripts
docker-compose.yml       local/development infrastructure
docker-compose.prod.yml  production VPS stack
```

## Local backend

```bash
cp .env.example .env
make infra-up
make api-install
make migrate
make api-run
```

FastAPI is available at `http://localhost:8000`; liveness is `GET /api/v1/health`, dependency readiness is `GET /api/v1/health/ready`, realtime delivery is `WS /api/v1/realtime`, and OpenAPI is available at `/docs`.

For the complete local infrastructure, including MinIO, migrations and the maintenance/realtime worker:

```bash
docker compose up -d
```

## Provision the first Mosala administrator

Public registration deliberately allows only house-seeker and landlord accounts. Create the initial administrator from a trusted server shell after migrations have run:

```bash
cd backend
mosala-provision-admin --phone YOUR_ADMIN_PHONE --name "Mosala Administrator"
```

The command securely prompts for the password without requiring it on the command line. An email can be supplied with `--email`. If a matching account already exists, the command refuses to change it unless `--update-existing` is supplied deliberately.

With the Compose backend image, the same command can be run through the migration service:

```bash
docker compose run --rm migrate mosala-provision-admin \
  --phone YOUR_ADMIN_PHONE \
  --name "Mosala Administrator"
```

Do not commit production credentials to this repository. When `APP_ENV=production`, the API refuses to start with the development JWT or object-storage secret defaults.

## Mobile authentication sessions

A successful login returns a short-lived JWT access token plus an opaque rotating refresh token. Only a SHA-256 hash of each refresh token is stored by the backend. The Flutter app keeps both credentials in secure storage and renews the access token automatically before expiry.

Refresh credentials are one-time use: `/api/v1/auth/refresh` rotates the refresh token on every successful renewal. Reuse of an already-consumed or revoked refresh token is treated as possible credential theft and revokes that token family. `/api/v1/auth/logout` revokes the current refresh session and `/api/v1/auth/logout-all` signs the user out from every active device session. The default refresh lifetime is 30 days and is configurable with `REFRESH_TOKEN_DAYS`.

## Realtime notification protocol

Authenticated clients connect to `/api/v1/realtime` and send the JWT in the first WebSocket frame rather than putting it in the URL:

```json
{"type":"authenticate","token":"<access-token>"}
```

The backend persists notifications first, then the worker relays undelivered notification events through per-user Redis Pub/Sub channels. Delivery is intentionally at-least-once; the Flutter client deduplicates events by notification ID. Offline clients still retrieve the authoritative notification history through the REST endpoint. WebSocket reconnects use the same token store, so renewed access tokens are picked up automatically.

## Flutter

The repository intentionally keeps the Dart application source independent from generated platform-runner boilerplate. On a developer workstation, generate the runner(s) required for local work without regenerating `lib/`:

```bash
cd mobile
flutter create --platforms=android,ios,web .
flutter pub get
flutter run
```

Do not regenerate `lib/` when adding platform runners.

### Android acceptance package

Pull requests and `main` builds include an **Android acceptance APK** gate. CI creates only the missing Android runner in its temporary workspace, restores the repository-controlled Flutter configuration, builds the application in release mode, verifies the APK, writes a SHA-256 checksum, and uploads both files as a GitHub Actions artifact for 14 days.

The acceptance APK proves the current Flutter code and native plugins compile into an Android package. It is **not** the Play Store production binary: CI does not contain Mosala's production signing keystore, release signing credentials, production API endpoint, or Google Maps Android API credential. Those values must be provisioned through the approved release environment rather than committed to Git.

## Production deployment

The production stack keeps PostgreSQL and Redis off public host ports, fronts the API and media service with Caddy automatic HTTPS, uses a non-root backend container, and includes guarded database/media backup and restore tooling.

Start by copying the production environment template:

```bash
cp deploy/.env.production.example deploy/.env.production
chmod 600 deploy/.env.production
```

After replacing every placeholder and pointing the API/media DNS records at the VPS:

```bash
make prod-validate
make prod-up
```

Back up before updates:

```bash
make prod-backup
```

The complete VPS, TLS, update, backup, restore and rollback procedure is in `docs/DEPLOYMENT.md`. Production secrets and local backups are ignored by Git.

## Implemented marketplace capabilities

- JWT authentication, rotating refresh sessions and role-based access control
- secure mobile token storage, automatic access-token renewal and all-device logout
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
- durable in-app notifications with authenticated WebSocket realtime delivery
- automatic Flutter WebSocket reconnect and duplicate-event protection
- admin marketplace analytics and landlord portfolio analytics
- immutable request-linked audit ledger with Flutter admin viewer
- automatic unpaid-booking expiry and upcoming-viewing reminders
- production-safe worker locking, dependency readiness probes and production-secret validation
- production TLS/reverse proxy, private data services and backup/restore operations

## Validation

CI validates both development and production Docker Compose configurations, checks deployment-script syntax, compiles the backend, applies the complete Alembic migration chain to PostgreSQL/PostGIS, runs ordinary backend tests plus the full rental-lifecycle acceptance gate, builds the non-root backend Docker image, runs Flutter analysis/tests, and on pull requests/`main` builds a release-mode Android acceptance APK with a checksum artifact.

Live payment-provider settlement and external mobile push delivery are intentionally not simulated; those integration slices require the selected production providers and credentials.

See `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/DEPLOYMENT.md` for the wider system design and operations guidance.
