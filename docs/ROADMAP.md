# Development roadmap

## Slice 1 — platform foundation

- repository layout
- FastAPI application
- PostgreSQL/PostGIS model
- Alembic migration
- Redis booking hold
- property radius search
- Flutter BLoC feed shell
- Docker local infrastructure

## Slice 2 — identity and landlord onboarding

- access/refresh token authentication
- phone/email verification
- role-based authorization
- landlord profile and identity verification
- admin verification queue

## Slice 3 — property publishing

- property/unit CRUD
- media upload and object storage
- amenities and security-feature checklist
- map pin/address integration
- listing packages and activation workflow

## Slice 4 — discovery

- API-backed feed
- radius/map search
- filters, pagination and sort
- favourites
- property details and unit availability

## Slice 5 — booking and money

- persistent bookings
- payment-provider adapter contract
- payment callbacks/idempotency
- platform ledger
- refunds/cancellations
- admin booking confirmation

## Slice 6 — occupancy lifecycle

- tenancy records
- tenant notice
- future availability
- automatic re-advertising
- move-out inspection
- maintenance requests

## Slice 7 — engagement and operations

- push/SMS/email notifications
- in-app messaging
- viewing requests
- verified reviews
- disputes and audit log
- admin analytics
