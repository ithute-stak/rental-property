import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.booking import (
    Booking,
    BookingPayment,
    BookingStatus,
    BookingStatusHistory,
    LedgerDirection,
    LedgerEntry,
    Notification,
    PaymentStatus,
)
from app.models.rental import Property, PropertyStatus, Unit, UnitStatus, User, UserRole
from app.models.tenancy import Tenancy, TenancyStatus
from app.schemas.booking import (
    BookingCreate,
    BookingDecision,
    BookingHoldRead,
    BookingPaymentSubmit,
    BookingRead,
)

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hold_key(unit_id: uuid.UUID) -> str:
    return f"booking-hold:unit:{unit_id}"


def _bookable_status(status_value: str) -> bool:
    return status_value in {UnitStatus.AVAILABLE.value, UnitStatus.VACATING_SOON.value}


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


def _history(
    db: AsyncSession,
    booking: Booking,
    to_status: str,
    actor_id: uuid.UUID | None,
    note: str | None = None,
) -> None:
    previous = booking.status
    booking.status = to_status
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            from_status=previous,
            to_status=to_status,
            actor_id=actor_id,
            note=note,
        )
    )


async def _release_unit_after_failed_booking(db: AsyncSession, unit: Unit) -> None:
    notice = await db.scalar(
        select(Tenancy).where(
            Tenancy.unit_id == unit.id,
            Tenancy.status == TenancyStatus.NOTICE_GIVEN.value,
        )
    )
    if notice is None:
        unit.status = UnitStatus.AVAILABLE.value
        return
    unit.status = (
        UnitStatus.VACATING_SOON.value
        if notice.allow_readvertise
        else UnitStatus.NOTICE_GIVEN.value
    )


async def _read_booking(db: AsyncSession, booking: Booking) -> BookingRead:
    unit = await db.get(Unit, booking.unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking unit no longer exists")
    property_row = await db.get(Property, unit.property_id)
    if property_row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking property no longer exists")
    payment = await db.scalar(select(BookingPayment).where(BookingPayment.booking_id == booking.id))
    if payment is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking payment record is missing")
    return BookingRead(
        id=booking.id,
        unit_id=booking.unit_id,
        property_id=property_row.id,
        property_title=property_row.title,
        unit_name=unit.name,
        seeker_id=booking.seeker_id,
        status=booking.status,
        move_in_date=booking.move_in_date,
        amount_due=booking.amount_due,
        currency=booking.currency,
        payment_status=payment.status,
        payment_method=payment.method,
        payment_reference=payment.reference,
        payment_due_at=booking.payment_due_at,
        created_at=booking.created_at,
    )


async def _booking_for_update(db: AsyncSession, booking_id: uuid.UUID) -> Booking:
    booking = await db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


@router.post("/holds/{unit_id}", response_model=BookingHoldRead)
async def acquire_booking_hold(
    unit_id: uuid.UUID,
    user: User = Depends(require_roles(UserRole.HOUSE_SEEKER.value, UserRole.TENANT.value)),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> BookingHoldRead:
    unit = await db.scalar(
        select(Unit)
        .join(Property, Property.id == Unit.property_id)
        .where(Unit.id == unit_id, Property.status == PropertyStatus.ACTIVE.value)
    )
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Available rental unit not found")
    if not _bookable_status(unit.status):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit is not available for booking")

    acquired = bool(
        await redis.set(
            _hold_key(unit_id),
            str(user.id),
            ex=settings.booking_hold_seconds,
            nx=True,
        )
    )
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unit is temporarily held by another booking",
        )

    return BookingHoldRead(
        unit_id=unit_id,
        acquired=True,
        expires_in_seconds=settings.booking_hold_seconds,
    )


@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    user: User = Depends(require_roles(UserRole.HOUSE_SEEKER.value, UserRole.TENANT.value)),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> BookingRead:
    if payload.move_in_date < date.today():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Move-in date cannot be in the past")

    hold_owner = await redis.get(_hold_key(payload.unit_id))
    if hold_owner != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Acquire a booking hold before creating the booking",
        )

    unit = await db.scalar(select(Unit).where(Unit.id == payload.unit_id).with_for_update())
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    property_row = await db.get(Property, unit.property_id)
    if property_row is None or property_row.status != PropertyStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Property is not open for bookings")
    if not _bookable_status(unit.status):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit is no longer available for booking")
    if unit.available_from is not None and payload.move_in_date < unit.available_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unit is only available from {unit.available_from.isoformat()}",
        )

    amount_due = unit.deposit if unit.deposit > 0 else unit.monthly_rent
    booking = Booking(
        unit_id=unit.id,
        seeker_id=user.id,
        status=BookingStatus.PENDING_PAYMENT.value,
        move_in_date=payload.move_in_date,
        amount_due=amount_due,
        currency="LSL",
        payment_due_at=_utcnow() + timedelta(minutes=60),
    )
    db.add(booking)
    await db.flush()
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            from_status=None,
            to_status=BookingStatus.PENDING_PAYMENT.value,
            actor_id=user.id,
            note="Booking created after a valid Redis hold",
        )
    )
    db.add(
        BookingPayment(
            booking_id=booking.id,
            amount=amount_due,
            currency="LSL",
            status=PaymentStatus.PENDING.value,
        )
    )
    unit.status = UnitStatus.BOOKING_PENDING.value
    _notify(
        db,
        property_row.owner_id,
        "booking_started",
        "New booking started",
        f"{user.display_name} started booking {unit.name} at {property_row.title}.",
        booking_id=str(booking.id),
        property_id=str(property_row.id),
        unit_id=str(unit.id),
    )
    await db.commit()
    await redis.delete(_hold_key(unit.id))
    await db.refresh(booking)
    return await _read_booking(db, booking)


@router.get("/mine", response_model=list[BookingRead])
async def list_my_bookings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BookingRead]:
    rows = await db.scalars(
        select(Booking).where(Booking.seeker_id == user.id).order_by(Booking.created_at.desc())
    )
    return [await _read_booking(db, booking) for booking in rows]


@router.get("/landlord", response_model=list[BookingRead])
async def list_landlord_bookings(
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> list[BookingRead]:
    query = select(Booking).join(Unit, Unit.id == Booking.unit_id).join(Property, Property.id == Unit.property_id)
    if user.role == UserRole.LANDLORD.value:
        query = query.where(Property.owner_id == user.id)
    rows = await db.scalars(query.order_by(Booking.created_at.desc()))
    return [await _read_booking(db, booking) for booking in rows]


@router.get("/admin/review", response_model=list[BookingRead])
async def list_admin_payment_review(
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> list[BookingRead]:
    rows = await db.scalars(
        select(Booking)
        .where(Booking.status == BookingStatus.PAYMENT_REVIEW.value)
        .order_by(Booking.created_at)
    )
    return [await _read_booking(db, booking) for booking in rows]


@router.post("/{booking_id}/payment", response_model=BookingRead)
async def submit_booking_payment(
    booking_id: uuid.UUID,
    payload: BookingPaymentSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingRead:
    booking = await _booking_for_update(db, booking_id)
    if booking.seeker_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Booking access denied")
    if booking.status not in {BookingStatus.PENDING_PAYMENT.value, BookingStatus.PAYMENT_REVIEW.value}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is not awaiting payment review")

    payment = await db.scalar(select(BookingPayment).where(BookingPayment.booking_id == booking.id))
    if payment is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment record not found")
    payment.method = payload.method
    payment.reference = payload.reference.strip()
    payment.status = PaymentStatus.SUBMITTED.value
    payment.submitted_at = _utcnow()
    if booking.status != BookingStatus.PAYMENT_REVIEW.value:
        _history(db, booking, BookingStatus.PAYMENT_REVIEW.value, user.id, "Payment submitted for admin verification")

    admins = await db.scalars(select(User).where(User.role == UserRole.ADMIN.value, User.is_active.is_(True)))
    for admin in admins:
        _notify(
            db,
            admin.id,
            "payment_review_required",
            "Booking payment needs review",
            f"Payment {payload.reference.strip()} for booking {booking.id} is ready for verification.",
            booking_id=str(booking.id),
        )

    await db.commit()
    await db.refresh(booking)
    return await _read_booking(db, booking)


@router.post("/{booking_id}/confirm", response_model=BookingRead)
async def confirm_booking(
    booking_id: uuid.UUID,
    payload: BookingDecision,
    admin: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> BookingRead:
    booking = await _booking_for_update(db, booking_id)
    if booking.status != BookingStatus.PAYMENT_REVIEW.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is not awaiting admin confirmation")

    payment = await db.scalar(select(BookingPayment).where(BookingPayment.booking_id == booking.id).with_for_update())
    if payment is None or payment.status != PaymentStatus.SUBMITTED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submitted payment is required")
    unit = await db.scalar(select(Unit).where(Unit.id == booking.unit_id).with_for_update())
    if unit is None or unit.status != UnitStatus.BOOKING_PENDING.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit booking state is invalid")
    property_row = await db.get(Property, unit.property_id)
    if property_row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Property not found")

    now = _utcnow()
    payment.status = PaymentStatus.CONFIRMED.value
    payment.confirmed_at = now
    payment.confirmed_by = admin.id
    booking.confirmed_at = now
    _history(db, booking, BookingStatus.CONFIRMED.value, admin.id, payload.note or "Payment verified by admin")
    unit.status = UnitStatus.BOOKED.value

    existing_ledger = await db.scalar(select(LedgerEntry.id).where(LedgerEntry.booking_id == booking.id))
    if existing_ledger is None:
        db.add_all(
            [
                LedgerEntry(
                    booking_id=booking.id,
                    payment_id=payment.id,
                    account="platform_clearing",
                    direction=LedgerDirection.DEBIT.value,
                    amount=payment.amount,
                    currency=payment.currency,
                    memo="Booking funds received by platform",
                ),
                LedgerEntry(
                    booking_id=booking.id,
                    payment_id=payment.id,
                    account="booking_funds_held",
                    direction=LedgerDirection.CREDIT.value,
                    amount=payment.amount,
                    currency=payment.currency,
                    memo="Booking funds held pending rental settlement",
                ),
            ]
        )

    _notify(
        db,
        booking.seeker_id,
        "booking_confirmed",
        "Your room is booked",
        f"Your booking for {unit.name} at {property_row.title} has been confirmed.",
        booking_id=str(booking.id),
    )
    _notify(
        db,
        property_row.owner_id,
        "booking_confirmed",
        "A rental unit has been booked",
        f"{unit.name} at {property_row.title} has been confirmed as booked.",
        booking_id=str(booking.id),
        unit_id=str(unit.id),
    )

    await db.commit()
    await db.refresh(booking)
    return await _read_booking(db, booking)


@router.post("/{booking_id}/reject", response_model=BookingRead)
async def reject_booking_payment(
    booking_id: uuid.UUID,
    payload: BookingDecision,
    admin: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> BookingRead:
    booking = await _booking_for_update(db, booking_id)
    if booking.status != BookingStatus.PAYMENT_REVIEW.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is not awaiting admin review")
    payment = await db.scalar(select(BookingPayment).where(BookingPayment.booking_id == booking.id).with_for_update())
    unit = await db.scalar(select(Unit).where(Unit.id == booking.unit_id).with_for_update())
    if payment is None or unit is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking records are incomplete")

    payment.status = PaymentStatus.REJECTED.value
    _history(db, booking, BookingStatus.REJECTED.value, admin.id, payload.note or "Payment rejected by admin")
    await _release_unit_after_failed_booking(db, unit)
    property_row = await db.get(Property, unit.property_id)
    _notify(
        db,
        booking.seeker_id,
        "booking_rejected",
        "Booking payment was not approved",
        payload.note or "The payment could not be verified. You can contact Mosala Rentals for assistance.",
        booking_id=str(booking.id),
    )
    if property_row is not None:
        _notify(
            db,
            property_row.owner_id,
            "booking_released",
            "Rental unit released",
            f"{unit.name} is available for booking again after a payment was rejected.",
            unit_id=str(unit.id),
        )

    await db.commit()
    await db.refresh(booking)
    return await _read_booking(db, booking)


@router.post("/{booking_id}/cancel", response_model=BookingRead)
async def cancel_booking(
    booking_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingRead:
    booking = await _booking_for_update(db, booking_id)
    if booking.seeker_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Booking access denied")
    if booking.status not in {BookingStatus.PENDING_PAYMENT.value, BookingStatus.PAYMENT_REVIEW.value}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirmed bookings cannot be cancelled here")

    unit = await db.scalar(select(Unit).where(Unit.id == booking.unit_id).with_for_update())
    if unit is not None:
        await _release_unit_after_failed_booking(db, unit)
        property_row = await db.get(Property, unit.property_id)
        if property_row is not None:
            _notify(
                db,
                property_row.owner_id,
                "booking_cancelled",
                "Booking cancelled",
                f"The pending booking for {unit.name} was cancelled and the unit can be offered again.",
                unit_id=str(unit.id),
                booking_id=str(booking.id),
            )
    booking.cancelled_at = _utcnow()
    _history(db, booking, BookingStatus.CANCELLED.value, user.id, "Cancelled by house seeker")
    await db.commit()
    await db.refresh(booking)
    return await _read_booking(db, booking)
