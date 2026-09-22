import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.rental import Unit, UnitStatus
from app.schemas.property import BookingHoldRead

router = APIRouter()


@router.post("/holds/{unit_id}", response_model=BookingHoldRead)
async def acquire_booking_hold(
    unit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> BookingHoldRead:
    unit = await db.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    if unit.status != UnitStatus.AVAILABLE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit is not available")

    key = f"booking-hold:unit:{unit_id}"
    acquired = bool(await redis.set(key, "held", ex=settings.booking_hold_seconds, nx=True))
    if not acquired:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit is temporarily held by another booking")

    return BookingHoldRead(
        unit_id=unit_id,
        acquired=True,
        expires_in_seconds=settings.booking_hold_seconds,
    )
