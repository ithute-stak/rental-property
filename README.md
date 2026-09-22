# Rental Property

Rental Property is a location-aware rental marketplace and occupancy-management platform for landlords, tenants, house seekers, and platform administrators.

The product follows the complete rental lifecycle:

`discover -> verify -> book -> occupy -> give notice -> vacate -> re-advertise`

## Stack

- Flutter + BLoC
- FastAPI
- PostgreSQL + PostGIS
- Alembic
- Redis
- WebSockets (planned in the real-time slice)
- Object storage (planned for property media/documents)

## Repository layout

```text
backend/     FastAPI application, SQLAlchemy models and Alembic migrations
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

FastAPI is then available at `http://localhost:8000`; health is `GET /api/v1/health` and OpenAPI is available at `/docs`.

## Flutter

The repository contains the application source and dependency manifest. On a workstation with Flutter installed, generate platform runners once if they are not present, then run the app:

```bash
cd mobile
flutter create --platforms=android,ios,web .
flutter pub get
flutter run
```

Do not regenerate `lib/` when adding platform runners.

## First implemented capabilities

- property and rentable-unit domain separation
- PostgreSQL/PostGIS point storage
- radius search with `ST_DWithin` and distance ordering
- property and unit lifecycle states
- Redis booking holds to prevent simultaneous reservation attempts
- Alembic initial schema migration
- Facebook-style Flutter property feed shell
- explicit BLoC loading/loaded/empty/failure states
- CI for backend migrations/tests and Flutter analysis/tests

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md` for the design and phased plan.
