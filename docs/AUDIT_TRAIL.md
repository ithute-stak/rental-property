# Mosala Rentals audit trail

Mosala Rentals keeps a database-backed, append-only audit trail for business-critical state changes. It is separate from ordinary application/access logs: access logs help diagnose requests, while audit events preserve who changed important marketplace or financial state and what the business state became.

## Guarantees

- Audit events are stored in PostgreSQL and are part of the same database transaction as the state change they describe.
- PostgreSQL rejects `UPDATE` and `DELETE` against `audit_events` through an append-only trigger.
- Each HTTP-originated event records the same `X-Request-ID` returned to the caller and written to API access logs, allowing an incident to be traced across both sources.
- Actor UUID and role are historical snapshots. They intentionally do not cascade if an account is later disabled or deleted.
- Automated worker actions have no actor user and are distinguishable from human actions.
- The audit service redacts detail keys containing password, token, secret, authorization, credential, or reference. Payment references are never intentionally stored in audit details.

## Audited business actions

Current actions include:

- `landlord.verification.approved`
- `landlord.verification.rejected`
- `property.approved`
- `property.rejected`
- `property.activated`
- `advert_charge.quoted`
- `advert_charge.waived`
- `advert_charge.payment_submitted`
- `advert_charge.payment_confirmed`
- `advert_charge.payment_rejected`
- `booking.created`
- `booking.payment_submitted`
- `booking.payment_confirmed`
- `booking.payment_rejected`
- `booking.cancelled`
- `booking.expired` (system/worker action)
- `tenancy.activated`
- `tenancy.notice_given`
- `tenancy.ended`
- `tenancy.inspection_completed`

Each event contains only the identifiers and business-state fields needed to understand the transition, such as before/after status, amount/currency, payment method, dates, property/unit IDs and tenant/owner IDs.

## Admin API

Only system administrators can read the audit trail:

```text
GET /api/v1/admin/audit
```

Supported filters:

- `action`
- `entity_type`
- `entity_id`
- `actor_id`
- `request_id`
- `since`
- `until`
- `limit` (1-500, default 100)

Results are newest-first. `request_id` is particularly useful when an administrator reports an unexpected change: search the audit event, then search API/Caddy logs for the same request ID.

## Operations and retention

Audit events are durable business records and are included in normal PostgreSQL backups. Do not truncate `audit_events` as part of log rotation. Ordinary container/Caddy logs may be rotated independently because they are not the source of truth for the audit ledger.

If Mosala later adopts a formal retention policy, archival should copy old audit rows to an approved immutable archive before any retention mechanism is introduced. The application currently provides no delete endpoint for audit records.
