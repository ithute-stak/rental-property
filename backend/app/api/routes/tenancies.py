import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.models.booking import Booking, BookingStatus, Notification
from app.models.rental import Property, Unit, UnitStatus, User, UserRole
from app.models.tenancy import Tenancy, TenancyStatus
from app.schemas.tenancy import TenantNoticeCreate, TenancyActivateRequest, TenancyRead

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _notify(
    db: AsyncSession,
    user_id: uuid.UUID,
    kind: str,
    title: str,
    body: str,
    **payload: str,
) -> None:
    db.add(
        Notification(
            user_id=user_id,
            notification_type=kind,
            title=title,
            body=body,
            payload=payload,
        )
    )


async def _read(db: AsyncSession, tenancy: Tenancy) -> TenancyRead:
    unit = await db.get(Unit, tenancy.unit_id)
    tenant = await db.get(User, tenancy.tenant_id)
    if unit is None or tenant is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenancy records are incomplete")
    property_row = await db.get(Property, unit.property_id)
    if property_row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenancy property is missing")
    return TenancyRead(
        id=tenancy.id,
        booking_id=tenancy.booking_id,
        unit_id=tenancy.unit_id,
        property_id=property_row.id,
        property_title=property_row.title,
        unit_name=unit.name,
        tenant_id=tenancy.tenant_id,
        tenant_name=tenant.display_name,
        status=tenancy.status,
        start_date=tenancy.start_date,
        expected_move_out=tenancy.expected_move_out,
        allow_readvertise=tenancy.allow_readvertise,
        created_at=tenancy.created_at,
    )


async def _tenancy_for_update(db: AsyncSession, tenancy_id: uuid.UUID) -> Tenancy:
    row = await db.scalar(select(Tenancy).where(Tenancy.id == tenancy_id).with_for_update())
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenancy not found")
    return row


async def _property_for_tenancy(db: AsyncSession, tenancy: Tenancy) -> tuple[Unit, Property]:
    unit = await db.get(Unit, tenancy.unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenancy unit is missing")
    property_row = await db.get(Property, unit.property_id)
    if property_row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenancy property is missing")
    return unit, property_row


def _require_property_access(property_row: Property, user: User) -> None:
    if user.role != UserRole.ADMIN.value and property_row.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenancy access denied")


@router.post("/activate", response_model=TenancyRead, status_code=status.HTTP_201_CREATED)
async def activate_tenancy(
    payload: TenancyActivateRequest,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> TenancyRead:
    booking = await db.scalar(select(Booking).where(Booking.id == payload.booking_id).with_for_update())
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.status != BookingStatus.CONFIRMED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only confirmed bookings can become tenancies")

    existing = await db.scalar(select(Tenancy).where(Tenancy.booking_id == booking.id))
    if existing is not None:
        return await _read(db, existing)

    unit = await db.scalar(select(Unit).where(Unit.id == booking.unit_id).with_for_update())
    if unit is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking unit not found")
    property_row = await db.get(Property, unit.property_id)
    if property_row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Property not found")
    _require_property_access(property_row, user)
    if unit.status != UnitStatus.BOOKED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit is not in booked state")

    tenant = await db.get(User, booking.seeker_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booked tenant account is missing")

    tenancy = Tenancy(
        booking_id=booking.id,
        unit_id=unit.id,
        tenant_id=tenant.id,
        status=TenancyStatus.ACTIVE.value,
        start_date=booking.move_in_date,
        allow_readvertise=True,
    )
    db.add(tenancy)
    await db.flush()
    unit.status = UnitStatus.OCCUPIED.value
    if tenant.role == UserRole.HOUSE_SEEKER.value:
        tenant.role = UserRole.TENANT.value

    _notify(
        db,
        tenant.id,
        "tenancy_activated",
        "Your tenancy is active",
        f"You are now checked in to {unit.name} at {property_row.title}.",
        tenancy_id=str(tenancy.id),
        property_id=str(property_row.id),
    )
    await db.commit()
    await db.refresh(tenancy)
    return await _read(db, tenancy)


@router.get("/mine", response_model=list[TenancyRead])
async def list_my_tenancies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TenancyRead]:
    rows = await db.scalars(
        select(Tenancy).where(Tenancy.tenant_id == user.id).order_by(Tenancy.created_at.desc())
    )
    return [await _read(db, row) for row in rows]


@router.get("/landlord", response_model=list[TenancyRead])
async def list_landlord_tenancies(
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> list[TenancyRead]:
    query = select(Tenancy).join(Unit, Unit.id == Tenancy.unit_id).join(Property, Property.id == Unit.property_id)
    if user.role == UserRole.LANDLORD.value:
        query = query.where(Property.owner_id == user.id)
    rows = await db.scalars(query.order_by(Tenancy.created_at.desc()))
    return [await _read(db, row) for row in rows]


@router.post("/{tenancy_id}/notice", response_model=TenancyRead)
async def give_notice(
    tenancy_id: uuid.UUID,
    payload: TenantNoticeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TenancyRead:
    tenancy = await _tenancy_for_update(db, tenancy_id)
    if tenancy.tenant_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenancy access denied")
    if tenancy.status != TenancyStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notice has already been given or tenancy has ended")
    if payload.expected_move_out <= date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Expected move-out date must be after today",
        )

    unit, property_row = await _property_for_tenancy(db, tenancy)
    tenancy.status = TenancyStatus.NOTICE_GIVEN.value
    tenancy.notice_given_at = _now()
    tenancy.expected_move_out = payload.expected_move_out
    tenancy.allow_readvertise = payload.allow_readvertise
    unit.available_from = payload.expected_move_out + timedelta(days=1)
    unit.status = (
        UnitStatus.VACATING_SOON.value
        if payload.allow_readvertise
        else UnitStatus.NOTICE_GIVEN.value
    )

    availability = unit.available_from.isoformat()
    _notify(
        db,
        property_row.owner_id,
        "tenant_notice_given",
        "Tenant has given notice",
        f"{user.display_name} plans to leave {unit.name} on {payload.expected_move_out.isoformat()}. Future availability starts {availability}.",
        tenancy_id=str(tenancy.id),
        unit_id=str(unit.id),
    )
    _notify(
        db,
        user.id,
        "notice_recorded",
        "Your notice was recorded",
        f"Your expected move-out date is {payload.expected_move_out.isoformat()}.",
        tenancy_id=str(tenancy.id),
    )
    await db.commit()
    await db.refresh(tenancy)
    return await _read(db, tenancy)


@router.post("/{tenancy_id}/end", response_model=TenancyRead)
async def end_tenancy(
    tenancy_id: uuid.UUID,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> TenancyRead:
    tenancy = await _tenancy_for_update(db, tenancy_id)
    if tenancy.status == TenancyStatus.ENDED.value:
        return await _read(db, tenancy)
    unit, property_row = await _property_for_tenancy(db, tenancy)
    _require_property_access(property_row, user)

    tenancy.status = TenancyStatus.ENDED.value
    tenancy.ended_at = _now()
    if unit.status not in {UnitStatus.BOOKED.value, UnitStatus.BOOKING_PENDING.value}:
        unit.status = UnitStatus.INSPECTION.value

    _notify(
        db,
        tenancy.tenant_id,
        "tenancy_ended",
        "Move-out recorded",
        f"Your tenancy for {unit.name} at {property_row.title} has been marked as ended.",
        tenancy_id=str(tenancy.id),
    )
    await db.commit()
    await db.refresh(tenancy)
    return await _read(db, tenancy)


@router.post("/{tenancy_id}/inspection-complete", response_model=TenancyRead)
async def complete_inspection(
    tenancy_id: uuid.UUID,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> TenancyRead:
    tenancy = await _tenancy_for_update(db, tenancy_id)
    unit, property_row = await _property_for_tenancy(db, tenancy)
    _require_property_access(property_row, user)
    if tenancy.status != TenancyStatus.ENDED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="End the tenancy before completing inspection")
    if unit.status == UnitStatus.INSPECTION.value:
        unit.status = UnitStatus.AVAILABLE.value
        unit.available_from = date.today()
        await db.commit()
    return await _read(db, tenancy)
