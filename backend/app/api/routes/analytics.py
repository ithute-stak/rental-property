from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.advertising import AdvertCharge, AdvertChargeStatus
from app.models.booking import Booking, BookingPayment, BookingStatus, PaymentStatus
from app.models.engagement import FavouriteProperty, ViewingRequest, ViewingStatus
from app.models.messaging import Conversation, Message
from app.models.rental import (
    LandlordProfile,
    Property,
    PropertyStatus,
    Unit,
    UnitStatus,
    User,
    UserRole,
    VerificationStatus,
)
from app.models.tenancy import Tenancy, TenancyStatus
from app.schemas.analytics import AdminAnalyticsOverview, LandlordAnalyticsOverview

router = APIRouter()


async def _count(db: AsyncSession, statement) -> int:
    return int(await db.scalar(statement) or 0)


@router.get("/admin/overview", response_model=AdminAnalyticsOverview)
async def admin_overview(
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> AdminAnalyticsOverview:
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    active_properties = await _count(
        db,
        select(func.count(Property.id)).where(Property.status == PropertyStatus.ACTIVE.value),
    )
    available_units = await _count(
        db,
        select(func.count(Unit.id))
        .join(Property, Property.id == Unit.property_id)
        .where(
            Property.status == PropertyStatus.ACTIVE.value,
            Unit.status == UnitStatus.AVAILABLE.value,
        ),
    )
    occupied_units = await _count(
        db,
        select(func.count(Unit.id)).where(Unit.status == UnitStatus.OCCUPIED.value),
    )
    vacating_soon_units = await _count(
        db,
        select(func.count(Unit.id)).where(Unit.status == UnitStatus.VACATING_SOON.value),
    )
    active_tenancies = await _count(
        db,
        select(func.count(Tenancy.id)).where(
            Tenancy.status.in_([
                TenancyStatus.ACTIVE.value,
                TenancyStatus.NOTICE_GIVEN.value,
            ])
        ),
    )
    pending_landlord_verifications = await _count(
        db,
        select(func.count(LandlordProfile.id)).where(
            LandlordProfile.verification_status == VerificationStatus.PENDING.value
        ),
    )
    pending_property_reviews = await _count(
        db,
        select(func.count(Property.id)).where(
            Property.status == PropertyStatus.PENDING_VERIFICATION.value
        ),
    )
    pending_booking_payment_reviews = await _count(
        db,
        select(func.count(Booking.id)).where(Booking.status == BookingStatus.PAYMENT_REVIEW.value),
    )
    pending_advert_payment_reviews = await _count(
        db,
        select(func.count(AdvertCharge.id)).where(
            AdvertCharge.status == AdvertChargeStatus.PAYMENT_SUBMITTED.value
        ),
    )
    open_viewing_requests = await _count(
        db,
        select(func.count(ViewingRequest.id)).where(
            ViewingRequest.status.in_([
                ViewingStatus.PENDING.value,
                ViewingStatus.RESCHEDULED.value,
            ])
        ),
    )
    confirmed_bookings_this_month = await _count(
        db,
        select(func.count(Booking.id)).where(
            Booking.status.in_([
                BookingStatus.CONFIRMED.value,
                BookingStatus.FULFILLED.value,
            ]),
            Booking.created_at >= month_start,
        ),
    )
    booking_funds_confirmed = await db.scalar(
        select(func.coalesce(func.sum(BookingPayment.amount), 0)).where(
            BookingPayment.status == PaymentStatus.CONFIRMED.value
        )
    )
    advert_revenue_confirmed = await db.scalar(
        select(func.coalesce(func.sum(AdvertCharge.amount), 0)).where(
            AdvertCharge.status == AdvertChargeStatus.PAID.value
        )
    )
    saved_homes = await _count(db, select(func.count(FavouriteProperty.id)))
    conversations = await _count(db, select(func.count(Conversation.id)))
    messages = await _count(db, select(func.count(Message.id)))

    return AdminAnalyticsOverview(
        active_properties=active_properties,
        available_units=available_units,
        occupied_units=occupied_units,
        vacating_soon_units=vacating_soon_units,
        active_tenancies=active_tenancies,
        pending_landlord_verifications=pending_landlord_verifications,
        pending_property_reviews=pending_property_reviews,
        pending_booking_payment_reviews=pending_booking_payment_reviews,
        pending_advert_payment_reviews=pending_advert_payment_reviews,
        open_viewing_requests=open_viewing_requests,
        confirmed_bookings_this_month=confirmed_bookings_this_month,
        booking_funds_confirmed=Decimal(str(booking_funds_confirmed or 0)),
        advert_revenue_confirmed=Decimal(str(advert_revenue_confirmed or 0)),
        saved_homes=saved_homes,
        conversations=conversations,
        messages=messages,
    )


@router.get("/landlord/overview", response_model=LandlordAnalyticsOverview)
async def landlord_overview(
    user: User = Depends(require_roles(UserRole.LANDLORD.value)),
    db: AsyncSession = Depends(get_db),
) -> LandlordAnalyticsOverview:
    properties = await _count(
        db,
        select(func.count(Property.id)).where(Property.owner_id == user.id),
    )
    active_properties = await _count(
        db,
        select(func.count(Property.id)).where(
            Property.owner_id == user.id,
            Property.status == PropertyStatus.ACTIVE.value,
        ),
    )
    total_units = await _count(
        db,
        select(func.count(Unit.id))
        .join(Property, Property.id == Unit.property_id)
        .where(Property.owner_id == user.id),
    )
    available_units = await _count(
        db,
        select(func.count(Unit.id))
        .join(Property, Property.id == Unit.property_id)
        .where(
            Property.owner_id == user.id,
            Unit.status == UnitStatus.AVAILABLE.value,
        ),
    )
    occupied_units = await _count(
        db,
        select(func.count(Unit.id))
        .join(Property, Property.id == Unit.property_id)
        .where(
            Property.owner_id == user.id,
            Unit.status == UnitStatus.OCCUPIED.value,
        ),
    )
    vacating_soon_units = await _count(
        db,
        select(func.count(Unit.id))
        .join(Property, Property.id == Unit.property_id)
        .where(
            Property.owner_id == user.id,
            Unit.status == UnitStatus.VACATING_SOON.value,
        ),
    )
    active_tenancies = await _count(
        db,
        select(func.count(Tenancy.id))
        .join(Unit, Unit.id == Tenancy.unit_id)
        .join(Property, Property.id == Unit.property_id)
        .where(
            Property.owner_id == user.id,
            Tenancy.status.in_([
                TenancyStatus.ACTIVE.value,
                TenancyStatus.NOTICE_GIVEN.value,
            ]),
        ),
    )
    pending_viewings = await _count(
        db,
        select(func.count(ViewingRequest.id))
        .join(Property, Property.id == ViewingRequest.property_id)
        .where(
            Property.owner_id == user.id,
            ViewingRequest.status.in_([
                ViewingStatus.PENDING.value,
                ViewingStatus.RESCHEDULED.value,
            ]),
        ),
    )
    confirmed_bookings = await _count(
        db,
        select(func.count(Booking.id))
        .join(Unit, Unit.id == Booking.unit_id)
        .join(Property, Property.id == Unit.property_id)
        .where(
            Property.owner_id == user.id,
            Booking.status.in_([
                BookingStatus.CONFIRMED.value,
                BookingStatus.FULFILLED.value,
            ]),
        ),
    )
    saved_homes = await _count(
        db,
        select(func.count(FavouriteProperty.id))
        .join(Property, Property.id == FavouriteProperty.property_id)
        .where(Property.owner_id == user.id),
    )
    conversations = await _count(
        db,
        select(func.count(Conversation.id)).where(Conversation.landlord_id == user.id),
    )
    unread_messages = await _count(
        db,
        select(func.count(Message.id))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.landlord_id == user.id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        ),
    )

    return LandlordAnalyticsOverview(
        properties=properties,
        active_properties=active_properties,
        total_units=total_units,
        available_units=available_units,
        occupied_units=occupied_units,
        vacating_soon_units=vacating_soon_units,
        active_tenancies=active_tenancies,
        pending_viewings=pending_viewings,
        confirmed_bookings=confirmed_bookings,
        saved_homes=saved_homes,
        conversations=conversations,
        unread_messages=unread_messages,
    )
