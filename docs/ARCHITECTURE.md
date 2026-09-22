# Architecture

## Guiding principles

1. A property and a rentable unit are different domain objects.
2. Availability is stateful and auditable, not a single boolean.
3. Location is a first-class field backed by PostGIS.
4. A booking starts with a short Redis hold so two users cannot reserve the same unit concurrently.
5. Financial records will use an immutable ledger rather than a `paid=true` flag.
6. Admin verification and landlord/tenant actions will be explicit workflows.

## Initial runtime

```text
Flutter
  -> HTTPS / WebSocket
FastAPI
  -> PostgreSQL + PostGIS
  -> Redis
  -> Object storage (next slice)
  -> payment adapters (next slice)
```

## Domain lifecycle

### Property

`draft -> pending_verification -> approved -> active`

Exceptional states: `rejected`, `suspended`.

### Unit

`available -> booking_pending -> booked -> occupied -> notice_given -> vacating_soon -> inspection -> available`

An `inactive` state is provided for units intentionally removed from the market.

## Search

Search starts in PostgreSQL/PostGIS. Text filters cover district/town while spatial queries use `ST_DWithin` and `ST_Distance`. A dedicated search engine can be introduced later if ranking, typo tolerance, synonyms, and large-scale faceting require it.

## Booking concurrency

`POST /api/v1/bookings/holds/{unit_id}` creates a Redis `SET NX EX` lock. The initial TTL is ten minutes. Payment orchestration will later convert a successful hold into a persisted booking inside a database transaction.
