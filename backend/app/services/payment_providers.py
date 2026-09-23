from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping, Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advertising import AdvertCharge, AdvertChargeStatus
from app.models.booking import (
    Booking,
    BookingPayment,
    BookingStatus,
    BookingStatusHistory,
    Notification,
    PaymentStatus,
)
from app.models.payment import PaymentProviderEvent
from app.models.rental import Property, Unit, User, UserRole
from app.services.audit import add_audit_event
from app.services.payments import PaymentReferenceConflict, claim_payment_reference, normalize_payment_reference

_PROVIDER_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
_ALLOWED_SOURCES = {"booking", "advert_charge"}
_ALLOWED_OUTCOMES = {"paid", "pending", "failed", "cancelled", "refunded"}


class PaymentProviderError(ValueError):
    pass


class PaymentWebhookSignatureError(PaymentProviderError):
    pass


class PaymentWebhookPayloadError(PaymentProviderError):
    pass


class PaymentWebhookConflict(PaymentProviderError):
    pass


@dataclass(frozen=True, slots=True)
class NormalizedPaymentEvent:
    event_id: str
    event_type: str
    provider_transaction_id: str | None
    source_type: str
    source_id: uuid.UUID
    outcome: str
    amount: Decimal | None = None
    currency: str | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PaymentWebhookResult:
    event: PaymentProviderEvent
    duplicate: bool


class PaymentProviderAdapter(Protocol):
    async def verify_and_parse(
        self,
        *,
        body: bytes,
        headers: Mapping[str, str],
    ) -> NormalizedPaymentEvent: ...


_adapters: dict[str, PaymentProviderAdapter] = {}


def normalize_provider_name(provider: str) -> str:
    normalized = provider.strip().lower()
    if not _PROVIDER_RE.fullmatch(normalized):
        raise PaymentWebhookPayloadError("Invalid payment provider name")
    return normalized


def register_payment_provider(provider: str, adapter: PaymentProviderAdapter) -> None:
    _adapters[normalize_provider_name(provider)] = adapter


def unregister_payment_provider(provider: str) -> None:
    try:
        normalized = normalize_provider_name(provider)
    except PaymentWebhookPayloadError:
        return
    _adapters.pop(normalized, None)


def get_payment_provider(provider: str) -> PaymentProviderAdapter | None:
    try:
        normalized = normalize_provider_name(provider)
    except PaymentWebhookPayloadError:
        return None
    return _adapters.get(normalized)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _validate_event(event: NormalizedPaymentEvent) -> NormalizedPaymentEvent:
    event_id = event.event_id.strip()
    event_type = event.event_type.strip()
    source_type = event.source_type.strip().lower()
    outcome = event.outcome.strip().lower()
    transaction_id = (
        event.provider_transaction_id.strip() if event.provider_transaction_id is not None else None
    )
    currency = event.currency.strip().upper() if event.currency is not None else None

    if not event_id or len(event_id) > 180:
        raise PaymentWebhookPayloadError("Provider event id is missing or too long")
    if not event_type or len(event_type) > 80:
        raise PaymentWebhookPayloadError("Provider event type is missing or too long")
    if source_type not in _ALLOWED_SOURCES:
        raise PaymentWebhookPayloadError("Unsupported payment source type")
    if outcome not in _ALLOWED_OUTCOMES:
        raise PaymentWebhookPayloadError("Unsupported payment outcome")
    if transaction_id is not None and (not transaction_id or len(transaction_id) > 180):
        raise PaymentWebhookPayloadError("Provider transaction id is invalid")
    if currency is not None and (len(currency) != 3 or not currency.isalpha()):
        raise PaymentWebhookPayloadError("Payment currency must be a three-letter code")
    if event.amount is not None and event.amount < 0:
        raise PaymentWebhookPayloadError("Payment amount cannot be negative")
    occurred_at = event.occurred_at
    if occurred_at is not None and occurred_at.tzinfo is None:
        raise PaymentWebhookPayloadError("Provider event time must include a timezone")

    return NormalizedPaymentEvent(
        event_id=event_id,
        event_type=event_type,
        provider_transaction_id=transaction_id,
        source_type=source_type,
        source_id=event.source_id,
        outcome=outcome,
        amount=event.amount,
        currency=currency,
        occurred_at=occurred_at,
    )


def _notify(
    db: AsyncSession,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: str,
    **payload: str,
) -> None:
    db.add(
        Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            payload=payload,
        )
    )


async def _notify_admins(
    db: AsyncSession,
    *,
    notification_type: str,
    title: str,
    body: str,
    **payload: str,
) -> None:
    admins = await db.scalars(
        select(User).where(User.role == UserRole.ADMIN.value, User.is_active.is_(True))
    )
    for admin in admins:
        _notify(db, admin.id, notification_type, title, body, **payload)


async def _manual_review(
    db: AsyncSession,
    row: PaymentProviderEvent,
    *,
    reason: str,
) -> None:
    row.processing_status = "manual_review"
    row.processing_message = reason
    await _notify_admins(
        db,
        notification_type="provider_payment_manual_review",
        title="Provider payment needs review",
        body=f"A {row.provider} payment callback needs reconciliation: {reason}",
        source_type=row.source_type,
        source_id=str(row.source_id),
        provider_event_id=str(row.id),
    )
    add_audit_event(
        db,
        actor=None,
        action="payment_provider.manual_review",
        entity_type=row.source_type,
        entity_id=row.source_id,
        details={
            "provider": row.provider,
            "outcome": row.outcome,
            "amount": row.amount,
            "currency": row.currency,
            "reason": reason,
        },
    )


def _matches_money(
    expected_amount: Decimal,
    expected_currency: str,
    event: NormalizedPaymentEvent,
) -> bool:
    return (
        event.amount is not None
        and event.currency is not None
        and Decimal(event.amount) == Decimal(expected_amount)
        and event.currency.upper() == expected_currency.upper()
    )


async def _process_booking_paid(
    db: AsyncSession,
    row: PaymentProviderEvent,
    event: NormalizedPaymentEvent,
) -> None:
    booking = await db.scalar(
        select(Booking).where(Booking.id == event.source_id).with_for_update()
    )
    if booking is None:
        await _manual_review(db, row, reason="Booking does not exist")
        return

    payment = await db.scalar(
        select(BookingPayment).where(BookingPayment.booking_id == booking.id).with_for_update()
    )
    if payment is None:
        await _manual_review(db, row, reason="Booking payment record is missing")
        return
    if not _matches_money(payment.amount, payment.currency, event):
        await _manual_review(db, row, reason="Provider amount or currency does not match booking")
        return
    if not event.provider_transaction_id:
        await _manual_review(db, row, reason="Paid callback is missing provider transaction id")
        return

    method = f"provider:{row.provider}"
    reference = normalize_payment_reference(event.provider_transaction_id)
    if (
        payment.method == method
        and payment.reference == reference
        and payment.status in {PaymentStatus.SUBMITTED.value, PaymentStatus.CONFIRMED.value}
        and booking.status
        in {
            BookingStatus.PAYMENT_REVIEW.value,
            BookingStatus.CONFIRMED.value,
            BookingStatus.FULFILLED.value,
        }
    ):
        row.processing_status = "processed"
        row.processing_message = "Provider payment was already applied to this booking"
        return

    if booking.status != BookingStatus.PENDING_PAYMENT.value or payment.status != PaymentStatus.PENDING.value:
        await _manual_review(
            db,
            row,
            reason=f"Booking/payment state is {booking.status}/{payment.status}, not payable",
        )
        return
    if booking.payment_due_at <= _utcnow():
        await _manual_review(db, row, reason="Provider payment arrived after booking deadline")
        return

    unit = await db.scalar(select(Unit).where(Unit.id == booking.unit_id).with_for_update())
    if unit is None:
        await _manual_review(db, row, reason="Booking unit no longer exists")
        return
    property_row = await db.get(Property, unit.property_id)
    if property_row is None:
        await _manual_review(db, row, reason="Booking property no longer exists")
        return

    try:
        await claim_payment_reference(
            db,
            method=method,
            reference=reference,
            source_type="booking",
            source_id=booking.id,
        )
    except PaymentReferenceConflict:
        await _manual_review(db, row, reason="Provider transaction is already claimed elsewhere")
        return

    previous_booking_status = booking.status
    previous_payment_status = payment.status
    payment.method = method
    payment.reference = reference
    payment.status = PaymentStatus.SUBMITTED.value
    payment.submitted_at = _utcnow()
    booking.status = BookingStatus.PAYMENT_REVIEW.value
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            from_status=previous_booking_status,
            to_status=booking.status,
            actor_id=None,
            note=f"Payment reported by provider {row.provider}; awaiting Mosala verification",
        )
    )
    await _notify_admins(
        db,
        notification_type="provider_booking_payment_review",
        title="Provider booking payment needs review",
        body=f"{row.provider} reported funds for booking {booking.id}. Verify before confirmation.",
        booking_id=str(booking.id),
        provider_event_id=str(row.id),
    )
    _notify(
        db,
        booking.seeker_id,
        "provider_payment_received",
        "Payment received",
        "Your payment provider reported the booking payment. Mosala is verifying it now.",
        booking_id=str(booking.id),
    )
    add_audit_event(
        db,
        actor=None,
        action="booking.provider_payment_received",
        entity_type="booking",
        entity_id=booking.id,
        details={
            "provider": row.provider,
            "from_status": previous_booking_status,
            "to_status": booking.status,
            "from_payment_status": previous_payment_status,
            "to_payment_status": payment.status,
            "amount": payment.amount,
            "currency": payment.currency,
        },
    )
    row.processing_status = "processed"
    row.processing_message = "Booking payment moved to Mosala verification queue"


async def _process_advert_paid(
    db: AsyncSession,
    row: PaymentProviderEvent,
    event: NormalizedPaymentEvent,
) -> None:
    charge = await db.scalar(
        select(AdvertCharge).where(AdvertCharge.id == event.source_id).with_for_update()
    )
    if charge is None:
        await _manual_review(db, row, reason="Advertising charge does not exist")
        return
    if not _matches_money(charge.amount, charge.currency, event):
        await _manual_review(db, row, reason="Provider amount or currency does not match advert charge")
        return
    if not event.provider_transaction_id:
        await _manual_review(db, row, reason="Paid callback is missing provider transaction id")
        return

    method = f"provider:{row.provider}"
    reference = normalize_payment_reference(event.provider_transaction_id)
    if (
        charge.payment_method == method
        and charge.payment_reference == reference
        and charge.status
        in {AdvertChargeStatus.PAYMENT_SUBMITTED.value, AdvertChargeStatus.PAID.value}
    ):
        row.processing_status = "processed"
        row.processing_message = "Provider payment was already applied to this advert charge"
        return

    if charge.status not in {
        AdvertChargeStatus.QUOTED.value,
        AdvertChargeStatus.PAYMENT_REJECTED.value,
    }:
        await _manual_review(db, row, reason=f"Advert charge state {charge.status} is not payable")
        return

    property_row = await db.get(Property, charge.property_id)
    if property_row is None:
        await _manual_review(db, row, reason="Advertising property no longer exists")
        return

    try:
        await claim_payment_reference(
            db,
            method=method,
            reference=reference,
            source_type="advert_charge",
            source_id=charge.id,
        )
    except PaymentReferenceConflict:
        await _manual_review(db, row, reason="Provider transaction is already claimed elsewhere")
        return

    previous_status = charge.status
    charge.payment_method = method
    charge.payment_reference = reference
    charge.payment_submitted_at = _utcnow()
    charge.status = AdvertChargeStatus.PAYMENT_SUBMITTED.value
    await _notify_admins(
        db,
        notification_type="provider_advert_payment_review",
        title="Provider advert payment needs review",
        body=f"{row.provider} reported funds for {property_row.title}. Verify before activation.",
        property_id=str(property_row.id),
        advert_charge_id=str(charge.id),
        provider_event_id=str(row.id),
    )
    _notify(
        db,
        property_row.owner_id,
        "provider_payment_received",
        "Advertising payment received",
        "Your payment provider reported the advertising payment. Mosala is verifying it now.",
        property_id=str(property_row.id),
    )
    add_audit_event(
        db,
        actor=None,
        action="advert_charge.provider_payment_received",
        entity_type="property",
        entity_id=property_row.id,
        details={
            "provider": row.provider,
            "advert_charge_id": charge.id,
            "from_status": previous_status,
            "to_status": charge.status,
            "amount": charge.amount,
            "currency": charge.currency,
        },
    )
    row.processing_status = "processed"
    row.processing_message = "Advertising payment moved to Mosala verification queue"


async def _process_event(
    db: AsyncSession,
    row: PaymentProviderEvent,
    event: NormalizedPaymentEvent,
) -> None:
    if event.outcome == "refunded":
        await _manual_review(db, row, reason="Provider reported a refund; reconciliation is required")
        return
    if event.outcome != "paid":
        row.processing_status = "recorded"
        row.processing_message = f"Provider outcome {event.outcome} recorded without state change"
        return

    if event.source_type == "booking":
        await _process_booking_paid(db, row, event)
    elif event.source_type == "advert_charge":
        await _process_advert_paid(db, row, event)
    else:  # Protected by _validate_event; kept defensive for future source types.
        await _manual_review(db, row, reason="Unsupported source type")


async def ingest_payment_webhook(
    db: AsyncSession,
    *,
    provider: str,
    body: bytes,
    headers: Mapping[str, str],
) -> PaymentWebhookResult:
    normalized_provider = normalize_provider_name(provider)
    adapter = get_payment_provider(normalized_provider)
    if adapter is None:
        raise LookupError(normalized_provider)

    event = _validate_event(await adapter.verify_and_parse(body=body, headers=headers))
    digest = hashlib.sha256(body).hexdigest()

    statement = (
        insert(PaymentProviderEvent)
        .values(
            provider=normalized_provider,
            event_id=event.event_id,
            event_type=event.event_type,
            provider_transaction_id=event.provider_transaction_id,
            source_type=event.source_type,
            source_id=event.source_id,
            outcome=event.outcome,
            amount=event.amount,
            currency=event.currency,
            occurred_at=event.occurred_at,
            payload_sha256=digest,
            processing_status="received",
        )
        .on_conflict_do_nothing(constraint="uq_payment_provider_event")
        .returning(PaymentProviderEvent.id)
    )
    created_id = await db.scalar(statement)
    if created_id is None:
        existing = await db.scalar(
            select(PaymentProviderEvent).where(
                PaymentProviderEvent.provider == normalized_provider,
                PaymentProviderEvent.event_id == event.event_id,
            )
        )
        if existing is None:
            raise RuntimeError("Provider event could not be resolved after idempotency conflict")
        if existing.payload_sha256 != digest:
            raise PaymentWebhookConflict(
                "The provider reused an event id with a different payload"
            )
        return PaymentWebhookResult(event=existing, duplicate=True)

    row = await db.get(PaymentProviderEvent, created_id)
    if row is None:
        raise RuntimeError("Created provider event could not be loaded")

    await _process_event(db, row, event)
    row.processed_at = _utcnow()
    await db.flush()
    return PaymentWebhookResult(event=row, duplicate=False)
