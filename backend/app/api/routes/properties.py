from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rental import Property, PropertyStatus
from app.schemas.property import PropertyCreate, PropertyRead

router = APIRouter()


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property(payload: PropertyCreate, db: AsyncSession = Depends(get_db)) -> Property:
    property_row = Property(
        **payload.model_dump(exclude={"latitude", "longitude"}),
        latitude=payload.latitude,
        longitude=payload.longitude,
        location=WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326),
        status=PropertyStatus.DRAFT.value,
    )
    db.add(property_row)
    await db.commit()
    await db.refresh(property_row)
    return property_row


@router.get("", response_model=list[PropertyRead])
async def list_properties(
    district: str | None = None,
    town: str | None = None,
    latitude: Decimal | None = Query(default=None, ge=-90, le=90),
    longitude: Decimal | None = Query(default=None, ge=-180, le=180),
    radius_km: Decimal = Query(default=10, gt=0, le=100),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[Property]:
    query = select(Property).where(Property.status.in_([PropertyStatus.APPROVED.value, PropertyStatus.ACTIVE.value]))

    if district:
        query = query.where(func.lower(Property.district) == district.lower())
    if town:
        query = query.where(func.lower(Property.town) == town.lower())
    if latitude is not None and longitude is not None:
        search_point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        query = query.where(func.ST_DWithin(Property.location, search_point, radius_km * 1000))
        query = query.order_by(func.ST_Distance(Property.location, search_point))
    else:
        query = query.order_by(Property.created_at.desc())

    rows = await db.scalars(query.limit(limit))
    return list(rows)
