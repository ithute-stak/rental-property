import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement
from sqlalchemy import cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_optional_user, require_roles
from app.core.database import get_db
from app.core.storage import storage
from app.models.booking import Booking, BookingStatus
from app.models.engagement import ViewingRequest, ViewingStatus
from app.models.media import PropertyMedia
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
from app.schemas.property import (
    PropertyCreate,
    PropertyFeedItem,
    PropertyRead,
    PropertyUpdate,
    PublicPropertyRead,
    UnitCreate,
    UnitRead,
    UnitUpdate,
)

router = APIRouter()


def _search_point(latitude: Decimal, longitude: Decimal):
    return cast(
        func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
        Geography(geometry_type="POINT", srid=4326),
    )


def _fuzzy_score(search_text: str):
    return func.greatest(
        func.similarity(func.coalesce(Property.title, ""), search_text),
        func.similarity(func.coalesce(Property.area, ""), search_text),
        func.similarity(func.coalesce(Property.town, ""), search_text),
        func.similarity(func.coalesce(Property.district, ""), search_text),
    )


async def _property_or_404(db: AsyncSession, property_id: uuid.UUID) -> Property:
    row = await db.get(Property, property_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return row


def _ensure_owner_or_admin(row: Property, user: User) -> None:
    if row.owner_id != user.id and user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this property",
        )


def _ensure_editable(row: Property) -> None:
    if row.status not in {PropertyStatus.DRAFT.value, PropertyStatus.REJECTED.value}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft or rejected properties can be edited",
        )


async def _can_view_exact_location(
    db: AsyncSession,
    row: Property,
    user: User | None,
) -> bool:
    if user is None:
        return False
    if row.owner_id == user.id or user.role == UserRole.ADMIN.value:
        return True

    accepted_viewing = await db.scalar(
        select(ViewingRequest.id)
        .where(
            ViewingRequest.property_id == row.id,
            ViewingRequest.requester_id == user.id,
            ViewingRequest.status == ViewingStatus.ACCEPTED.value,
        )
        .limit(1)
    )
    if accepted_viewing is not None:
        return True

    confirmed_booking = await db.scalar(
        select(Booking.id)
        .join(Unit, Unit.id == Booking.unit_id)
        .where(
            Unit.property_id == row.id,
            Booking.seeker_id == user.id,
            Booking.status.in_([
                BookingStatus.CONFIRMED.value,
                BookingStatus.FULFILLED.value,
            ]),
        )
        .limit(1)
    )
    return confirmed_booking is not None


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property(
    payload: PropertyCreate,
    user: User = Depends(require_roles(UserRole.LANDLORD.value)),
    db: AsyncSession = Depends(get_db),
) -> Property:
    property_row = Property(
        **payload.model_dump(exclude={"latitude", "longitude"}),
        owner_id=user.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location=WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326),
        status=PropertyStatus.DRAFT.value,
    )
    db.add(property_row)
    await db.commit()
    await db.refresh(property_row)
    return property_row


@router.get("/feed", response_model=list[PropertyFeedItem])
async def property_feed(
    q: str | None = Query(default=None, max_length=120),
    district: str | None = Query(default=None, max_length=100),
    town: str | None = Query(default=None, max_length=100),
    min_rent: Decimal | None = Query(default=None, ge=0),
    max_rent: Decimal | None = Query(default=None, ge=0),
    latitude: Decimal | None = Query(default=None, ge=-90, le=90),
    longitude: Decimal | None = Query(default=None, ge=-180, le=180),
    radius_km: Decimal = Query(default=10, gt=0, le=100),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[PropertyFeedItem]:
    if min_rent is not None and max_rent is not None and min_rent > max_rent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Minimum rent cannot exceed maximum rent",
        )
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Latitude and longitude must be supplied together",
        )

    available_statuses = [UnitStatus.AVAILABLE.value, UnitStatus.VACATING_SOON.value]
    available_rooms = func.count(Unit.id).label("available_rooms")
    monthly_rent = func.min(Unit.monthly_rent).label("monthly_rent")
    cover_object_key = (
        select(PropertyMedia.object_key)
        .where(
            PropertyMedia.property_id == Property.id,
            PropertyMedia.is_cover.is_(True),
        )
        .order_by(PropertyMedia.created_at)
        .limit(1)
        .correlate(Property)
        .scalar_subquery()
        .label("cover_object_key")
    )

    query = (
        select(Property, available_rooms, monthly_rent, cover_object_key)
        .join(Unit, Unit.property_id == Property.id)
        .where(
            Property.status == PropertyStatus.ACTIVE.value,
            Unit.status.in_(available_statuses),
        )
        .group_by(Property.id)
    )

    search_score = None
    if q and q.strip():
        search_text = q.strip()
        term = f"%{search_text}%"
        search_score = _fuzzy_score(search_text)
        query = query.where(
            or_(
                Property.title.ilike(term),
                Property.area.ilike(term),
                Property.town.ilike(term),
                Property.district.ilike(term),
                search_score >= 0.18,
            )
        )
    if district:
        query = query.where(func.lower(Property.district) == district.strip().lower())
    if town:
        query = query.where(func.lower(Property.town) == town.strip().lower())
    if min_rent is not None:
        query = query.where(Unit.monthly_rent >= min_rent)
    if max_rent is not None:
        query = query.where(Unit.monthly_rent <= max_rent)

    if latitude is not None and longitude is not None:
        search_point = _search_point(latitude, longitude)
        distance_metres = float(radius_km) * 1000
        distance = func.ST_Distance(Property.location, search_point)
        query = query.where(func.ST_DWithin(Property.location, search_point, distance_metres))
        if search_score is not None:
            query = query.order_by(search_score.desc(), distance)
        else:
            query = query.order_by(distance)
    elif search_score is not None:
        query = query.order_by(search_score.desc(), Property.created_at.desc())
    else:
        query = query.order_by(Property.created_at.desc())

    result = await db.execute(query.limit(limit))
    return [
        PropertyFeedItem(
            id=property_row.id,
            title=property_row.title,
            district=property_row.district,
            town=property_row.town,
            area=property_row.area,
            security_level=property_row.security_level,
            monthly_rent=rent,
            available_rooms=room_count,
            image_url=storage.public_url(cover_key) if cover_key else None,
        )
        for property_row, room_count, rent, cover_key in result.all()
    ]


@router.get("", response_model=list[PublicPropertyRead])
async def list_properties(
    district: str | None = None,
    town: str | None = None,
    latitude: Decimal | None = Query(default=None, ge=-90, le=90),
    longitude: Decimal | None = Query(default=None, ge=-180, le=180),
    radius_km: Decimal = Query(default=10, gt=0, le=100),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[PublicPropertyRead]:
    query = select(Property).where(Property.status == PropertyStatus.ACTIVE.value)

    if district:
        query = query.where(func.lower(Property.district) == district.strip().lower())
    if town:
        query = query.where(func.lower(Property.town) == town.strip().lower())
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Latitude and longitude must be supplied together",
        )
    if latitude is not None and longitude is not None:
        search_point = _search_point(latitude, longitude)
        distance_metres = float(radius_km) * 1000
        query = query.where(func.ST_DWithin(Property.location, search_point, distance_metres))
        query = query.order_by(func.ST_Distance(Property.location, search_point))
    else:
        query = query.order_by(Property.created_at.desc())

    rows = await db.scalars(query.limit(limit))
    return [PublicPropertyRead.model_validate(row) for row in rows]


@router.get("/mine", response_model=list[PropertyRead])
async def list_my_properties(
    user: User = Depends(require_roles(UserRole.LANDLORD.value)),
    db: AsyncSession = Depends(get_db),
) -> list[Property]:
    rows = await db.scalars(
        select(Property).where(Property.owner_id == user.id).order_by(Property.created_at.desc())
    )
    return list(rows)


@router.get("/{property_id}", response_model=PropertyRead | PublicPropertyRead)
async def get_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> PropertyRead | PublicPropertyRead:
    row = await _property_or_404(db, property_id)
    if row.status != PropertyStatus.ACTIVE.value:
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        _ensure_owner_or_admin(row, user)
        return PropertyRead.model_validate(row)

    if await _can_view_exact_location(db, row, user):
        return PropertyRead.model_validate(row)
    return PublicPropertyRead.model_validate(row)


@router.patch("/{property_id}", response_model=PropertyRead)
async def update_property(
    property_id: uuid.UUID,
    payload: PropertyUpdate,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> Property:
    row = await _property_or_404(db, property_id)
    _ensure_owner_or_admin(row, user)
    _ensure_editable(row)

    changes = payload.model_dump(exclude_unset=True)
    latitude = changes.pop("latitude", None)
    longitude = changes.pop("longitude", None)
    for key, value in changes.items():
        setattr(row, key, value)

    if latitude is not None or longitude is not None:
        new_latitude = latitude if latitude is not None else row.latitude
        new_longitude = longitude if longitude is not None else row.longitude
        row.latitude = new_latitude
        row.longitude = new_longitude
        row.location = WKTElement(f"POINT({new_longitude} {new_latitude})", srid=4326)

    await db.commit()
    await db.refresh(row)
    return row


@router.post("/{property_id}/units", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
async def create_unit(
    property_id: uuid.UUID,
    payload: UnitCreate,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> Unit:
    row = await _property_or_404(db, property_id)
    _ensure_owner_or_admin(row, user)
    _ensure_editable(row)

    unit = Unit(
        property_id=row.id,
        name=payload.name,
        monthly_rent=payload.monthly_rent,
        deposit=payload.deposit,
        available_from=payload.available_from,
        status=UnitStatus.AVAILABLE.value,
    )
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return unit


@router.get("/{property_id}/units", response_model=list[UnitRead])
async def list_units(
    property_id: uuid.UUID,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> list[Unit]:
    row = await _property_or_404(db, property_id)
    if row.status != PropertyStatus.ACTIVE.value:
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        _ensure_owner_or_admin(row, user)
    units = await db.scalars(select(Unit).where(Unit.property_id == row.id).order_by(Unit.created_at))
    return list(units)


@router.patch("/{property_id}/units/{unit_id}", response_model=UnitRead)
async def update_unit(
    property_id: uuid.UUID,
    unit_id: uuid.UUID,
    payload: UnitUpdate,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> Unit:
    row = await _property_or_404(db, property_id)
    _ensure_owner_or_admin(row, user)
    _ensure_editable(row)

    unit = await db.scalar(select(Unit).where(Unit.id == unit_id, Unit.property_id == property_id))
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(unit, key, value)

    await db.commit()
    await db.refresh(unit)
    return unit


@router.delete("/{property_id}/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    property_id: uuid.UUID,
    unit_id: uuid.UUID,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> None:
    row = await _property_or_404(db, property_id)
    _ensure_owner_or_admin(row, user)
    _ensure_editable(row)

    unit = await db.scalar(select(Unit).where(Unit.id == unit_id, Unit.property_id == property_id))
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

    await db.delete(unit)
    await db.commit()


@router.post("/{property_id}/submit", response_model=PropertyRead)
async def submit_property(
    property_id: uuid.UUID,
    user: User = Depends(require_roles(UserRole.LANDLORD.value)),
    db: AsyncSession = Depends(get_db),
) -> Property:
    row = await _property_or_404(db, property_id)
    _ensure_owner_or_admin(row, user)
    _ensure_editable(row)

    profile = await db.scalar(select(LandlordProfile).where(LandlordProfile.user_id == user.id))
    if profile is None or profile.verification_status != VerificationStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Landlord verification must be approved before submitting a property",
        )

    unit_count = await db.scalar(select(func.count(Unit.id)).where(Unit.property_id == row.id))
    if not unit_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Add at least one rental unit before submitting the property",
        )

    row.status = PropertyStatus.PENDING_VERIFICATION.value
    await db.commit()
    await db.refresh(row)
    return row
