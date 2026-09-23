# Payment provider integration contract

Mosala Rentals keeps manual payment-reference submission and Mosala administrator verification as the fallback payment flow. External payment providers plug into a separate webhook boundary; a provider callback never bypasses Mosala's existing confirmation rules.

## Safety model

`POST /api/v1/payments/webhooks/{provider}` is public by design because payment providers call it server-to-server. Authentication comes from the registered provider adapter, which must verify the provider's real signature scheme before returning a normalized event.

The route:

- rejects unknown providers;
- limits webhook bodies to 64 KiB;
- requires adapter signature verification before database mutation;
- stores a SHA-256 digest instead of the raw provider payload;
- enforces `(provider, event_id)` uniqueness in PostgreSQL;
- returns the existing receipt for an exact replay;
- rejects reuse of the same event ID with a different payload digest; and
- records minimal normalized event metadata for reconciliation and audit.

Do not log or persist provider secrets, authorization headers, full mobile-money payloads, identity numbers, card data, or other unnecessary payer information.

## Normalized event

A provider adapter maps its provider-specific callback into `NormalizedPaymentEvent` with:

- provider event ID and event type;
- provider transaction ID when available;
- Mosala source type: `booking` or `advert_charge`;
- Mosala source UUID;
- outcome: `paid`, `pending`, `failed`, `cancelled`, or `refunded`;
- amount and ISO-style three-letter currency when supplied; and
- provider event timestamp when supplied.

The provider should carry Mosala's source UUID in its merchant reference/metadata when the payment is initiated. A future provider-specific checkout adapter can generate that metadata; the webhook layer is deliberately independent of checkout UX.

## Business-state handling

A verified `paid` event must exactly match the expected amount and currency and contain a provider transaction ID.

For a payable booking, the callback sets the payment to `submitted` and moves the booking from `pending_payment` to `payment_review`. Mosala administrators still perform the existing final confirmation, which books the unit and creates ledger entries.

For an advertising charge, the callback moves a quoted/rejected charge to `payment_submitted`. Mosala administrators still confirm the advertising payment before the property can be activated.

The callback does **not** automatically confirm funds, activate adverts, book units, or create a tenancy.

Late payments, amount/currency mismatches, transaction-reference conflicts, payments against invalid business states, and provider-reported refunds are recorded as `manual_review` and surfaced to administrators for reconciliation. Pending/failed/cancelled callbacks are recorded without changing the rental state so legitimate retries remain possible.

## Admin reconciliation queue

Provider callbacks that require human reconciliation are available only to Mosala administrators under `/api/v1/admin/payment-reconciliation`.

- `GET /events` returns the manual-review queue by default and supports provider, source type, source id, status, limit and offset filters.
- `GET /events/{event_id}` returns one normalized provider event.
- `POST /events/{event_id}/resolve` closes a `manual_review` case with a required reconciliation note.

Resolution never changes a booking, advert charge, tenancy, ledger entry or payment confirmation by itself. An administrator must use the existing business-specific verification action when funds genuinely need to be confirmed or rejected. Resolving the provider event only records that the exception was investigated.

A resolved event stores the resolver, resolution timestamp and note, while preserving the original processing reason. The action also creates an audit event named `payment_provider.reconciliation_resolved`. Raw provider payloads and payload hashes are intentionally not exposed by the admin reconciliation API.

## Adding a real provider

Implement `PaymentProviderAdapter.verify_and_parse`, then register it under a stable lowercase provider name during application startup. Provider-specific secrets belong in protected production environment variables/secrets, never in Git.

Before enabling a production adapter, add contract tests using the provider's documented signature algorithm and representative sanitized webhook fixtures. Test at least valid signature, invalid signature, exact replay, altered replay, paid callback, amount mismatch, late payment, refund, provider retry behavior and reconciliation visibility.

The generic webhook infrastructure intentionally contains no Lesotho provider credentials or guessed API contract. Add a concrete adapter only from the provider's official integration documentation and issued merchant credentials.
