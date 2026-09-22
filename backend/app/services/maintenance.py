from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import (
    Booking,
    BookingPayment,
    BookingStatus,
    BookingStatusHistory,
    Notification,
    PaymentStatus,
)
from app.models.engagement import ViewingRequest, ViewingStatus
from app.models.rental import Property, Unit, UnitStatus
from app.models.tenancy import Tenancy, TenancyStatus


@dataclass(frozen=True)
class MaintenanceResult:
    expired_bookings: int = 0
    viewing_reminders: int = 0


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def unit_status_after_booking_release(notice: Tenancy | None) -> str:
    if notice is None:
        return UnitStatus.AVAILABLE.value
    if notice.allow_readvertise:
        return UnitStatus.VACATING_SOON.value
    return UnitStatus.NOTICE_GIVEN.value


async def _active_notice(db: AsyncSession, unit_id) -> Tenancy | None:
    return await db.scalar(
        select(Tenancy).where(
            Tenancy.unit_id == unit_id,
            Tenancy.status == TenancyStatus.NOTICE_GIVEN.value,
        )
    )


def _notify(
    db: AsyncSession,
    user_id,
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


async def expire_stale_bookings(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> int:
    current = now or utcnow()
    rows = await db.scalars(
        select(Booking)
        .where(
            Booking.status == BookingStatus.PENDING_PAYMENT.value,
            Booking.payment_due_at <= current,
        )
        .order_by(Booking.payment_due_at)
        .with_for_update(skip_locked=True)
    )
    bookings = list(rows)
    expired = 0

    for booking in bookings:
        unit = await db.scalar(
            select(Unit).where(Unit.id == booking.unit_id).with_for_update()
        )
        if unit is None:
            continue
        payment = await db.scalar(
            select(BookingPayment)
            .where(BookingPayment.booking_id == booking.id)
            .with_for_update()
        )
        previous_status = booking.status
        booking.status = BookingStatus.EXPIRED.value
        if payment is not None and payment.status == PaymentStatus.PENDING.value:
            payment.status = PaymentStatus.EXPIRED.value
        db.add(
            BookingStatusHistory(
                booking_id=booking.id,
                from_status=previous_status,
                to_status=BookingStatus.EXPIRED.value,
                actor_id=None,
                note="Payment deadline expired automatically",
            )
        )

        if unit.status == UnitStatus.BOOKING_PENDING.value:
            notice = await _active_notice(db, unit.id)
            unit.status = unit_status_after_booking_release(notice)

        property_row = await db.get(Property, unit.property_id)
        _notify(
            db,
            booking.seeker_id,
            "booking_expired",
            "Booking expired",
            "The booking payment deadline passed and the rental unit was released.",
            booking_id=str(booking.id),
            unit_id=str(unit.id),
        )
        if property_row is not None:
            _notify(
                db,
                property_row.owner_id,
                "booking_released",
                "Unpaid booking released",
                f"The unpaid booking for {unit.name} at {property_row.title} expired automatically.",
                booking_id=str(booking.id),
                unit_id=str(unit.id),
                property_id=str(property_row.id),
            )
        expired += 1

    return expired


async def send_upcoming_viewing_reminders(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    reminder_hours: int = 24,
) -> int:
    current = now or utcnow()
    deadline = current + timedelta(hours=reminder_hours)
    rows = await db.scalars(
        select(ViewingRequest)
        .where(
            ViewingRequest.status == ViewingStatus.ACCEPTED.value,
            ViewingRequest.scheduled_at.is_not(None),
            ViewingRequest.scheduled_at > current,
            ViewingRequest.scheduled_at <= deadline,
            ViewingRequest.reminder_sent_at.is_(None),
        )
        .order_by(ViewingRequest.scheduled_at)
        .with_for_update(skip_locked=True)
    )
    reminders = 0

    for viewing in rows:
        property_row = await db.get(Property, viewing.property_id)
        if property_row is None or viewing.scheduled_at is None:
            continue
        scheduled = viewing.scheduled_at.isoformat()
        _notify(
            db,
            viewing.requester_id,
            "viewing_reminder",
            "Upcoming property viewing",
            f"Your viewing for {property_row.title} is scheduled for {scheduled}.",
            viewing_id=str(viewing.id),
            property_id=str(property_row.id),
        )
        _notify(
            db,
            property_row.owner_id,
            "viewing_reminder",
            "Upcoming property viewing",
            f"A viewing for {property_row.title} is scheduled for {scheduled}.",
            viewing_id=str(viewing.id),
            property_id=str(property_row.id),
        )
        viewing.reminder_sent_at = current
        reminders += 1

    return reminders


async def run_maintenance(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    viewing_reminder_hours: int = 24,
) -> MaintenanceResult:
    current = now or utcnow()
    expired = await expire_stale_bookings(db, now=current)
    reminders = await send_upcoming_viewing_reminders(
        db,
        now=current,
        reminder_hours=viewing_reminder_hours,
    )
    await db.commit()
    return MaintenanceResult(expired_bookings=expired, viewing_reminders=reminders)
