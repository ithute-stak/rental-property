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

## Repository layout

```text
backend/     FastAPI API, workers, models, migrations and tests
mobile/      Flutter client
docs/        architecture and delivery roadmap
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

## Authentication sessions

Access tokens remain short-lived JWTs. Login also issues a long-lived opaque refresh token. Only its SHA-256 hash is stored by the backend. Refresh tokens rotate every time `/api/v1/auth/refresh` is used; replay of an already-used refresh token revokes the whole token family as a theft/reuse precaution. `/api/v1/auth/logout` revokes the current refresh session and `/api/v1/auth/logout-all` revokes every device session for the authenticated account.

Flutter stores both credentials in secure storage. Existing authenticated API repositories continue requesting the current access token through the token store; when the JWT approaches expiry, the store performs one shared refresh operation and persists the rotated pair before returning the access token. This also gives WebSocket reconnects a current access token without duplicating refresh logic throughout the app.

## Realtime notification protocol

Authenticated clients connect to `/api/v1/realtime` and send the JWT in the first WebSocket frame rather than putting it in the URL:

```json
{"type":"authenticate","token":"<access-token>"}
```

The backend persists notifications first, then the worker relays undelivered notification events through per-user Redis Pub/Sub channels. Delivery is intentionally at-least-once; the Flutter client deduplicates events by notification ID. Offline clients still retrieve the authoritative notification history through the REST endpoint.

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

- JWT authentication, rotating refresh sessions and role-based access control
- secure Flutter token persistence with automatic access-token renewal
- server-side current-device and all-device session revocation
- refresh-token replay detection and family revocation
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
- automatic unpaid-booking expiry and upcoming-viewing reminders
- production-safe worker locking, dependency readiness probes and production-secret validation

## Validation

CI validates Docker Compose, compiles the backend, applies the complete Alembic migration chain to PostgreSQL/PostGIS, runs backend tests, builds the backend Docker image, runs Flutter analysis and executes Flutter tests.

Live payment-provider settlement and external mobile push delivery are intentionally not simulated; those integration slices require the selected production providers and credentials.

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md` for the wider system design and delivery plan.
