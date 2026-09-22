import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.core.storage import storage
from app.models.booking import Notification
from app.models.engagement import FavouriteProperty, ViewingRequest, ViewingStatus
from app.models.media import PropertyMedia
from app.models.rental import Property, PropertyStatus, Unit, UnitStatus, User, UserRole
from app.schemas.engagement import (
    FavouriteRead,
    ViewingDecision,
    ViewingRead,
    ViewingRequestCreate,
)

router = APIRouter()


async def _property_or_404(db: AsyncSession, property_id: uuid.UUID) -> Property:
    row = await db.get(Property, property_id)
    if row is None or row.status != PropertyStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active property not found")
    return row


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


async def _viewing_read(db: AsyncSession, row: ViewingRequest) -> ViewingRead:
    property_row = await db.get(Property, row.property_id)
    requester = await db.get(User, row.requester_id)
    if property_row is None or requester is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Viewing request records are incomplete")
    return ViewingRead(
        id=row.id,
        property_id=row.property_id,
        property_title=property_row.title,
        requester_id=row.requester_id,
        requester_name=requester.display_name,
        status=row.status,
        preferred_at=row.preferred_at,
        scheduled_at=row.scheduled_at,
        message=row.message,
        response_note=row.response_note,
        created_at=row.created_at,
    )


@router.post("/favourites/{property_id}", response_model=FavouriteRead, status_code=status.HTTP_201_CREATED)
async def save_property(
    property_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FavouriteRead:
    property_row = await _property_or_404(db, property_id)
    favourite = await db.scalar(
        select(FavouriteProperty).where(
            FavouriteProperty.user_id == user.id,
            FavouriteProperty.property_id == property_id,
        )
    )
    if favourite is None:
        favourite = FavouriteProperty(user_id=user.id, property_id=property_id)
        db.add(favourite)
        await db.commit()
        await db.refresh(favourite)

    available_statuses = [UnitStatus.AVAILABLE.value, UnitStatus.VACATING_SOON.value]
    rent, room_count = (
        await db.execute(
            select(func.min(Unit.monthly_rent), func.count(Unit.id)).where(
                Unit.property_id == property_id,
                Unit.status.in_(available_statuses),
            )
        )
    ).one()
    cover = await db.scalar(
        select(PropertyMedia).where(
            PropertyMedia.property_id == property_id,
            PropertyMedia.is_cover.is_(True),
        )
    )
    return FavouriteRead(
        property_id=property_row.id,
        title=property_row.title,
        town=property_row.town,
        area=property_row.area,
        monthly_rent=rent,
        available_rooms=room_count or 0,
        image_url=storage.public_url(cover.object_key) if cover else None,
        created_at=favourite.created_at,
    )


@router.delete("/favourites/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_property(
    property_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    favourite = await db.scalar(
        select(FavouriteProperty).where(
            FavouriteProperty.user_id == user.id,
            FavouriteProperty.property_id == property_id,
        )
    )
    if favourite is not None:
        await db.delete(favourite)
        await db.commit()


@router.get("/favourites", response_model=list[FavouriteRead])
async def list_favourites(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FavouriteRead]:
    favourites = await db.scalars(
        select(FavouriteProperty)
        .where(FavouriteProperty.user_id == user.id)
        .order_by(FavouriteProperty.created_at.desc())
    )
    result: list[FavouriteRead] = []
    for favourite in favourites:
        property_row = await db.get(Property, favourite.property_id)
        if property_row is None or property_row.status != PropertyStatus.ACTIVE.value:
            continue
        available_statuses = [UnitStatus.AVAILABLE.value, UnitStatus.VACATING_SOON.value]
        rent, room_count = (
            await db.execute(
                select(func.min(Unit.monthly_rent), func.count(Unit.id)).where(
                    Unit.property_id == property_row.id,
                    Unit.status.in_(available_statuses),
                )
            )
        ).one()
        cover = await db.scalar(
            select(PropertyMedia).where(
                PropertyMedia.property_id == property_row.id,
                PropertyMedia.is_cover.is_(True),
            )
        )
        result.append(
            FavouriteRead(
                property_id=property_row.id,
                title=property_row.title,
                town=property_row.town,
                area=property_row.area,
                monthly_rent=rent,
                available_rooms=room_count or 0,
                image_url=storage.public_url(cover.object_key) if cover else None,
                created_at=favourite.created_at,
            )
        )
    return result


@router.post("/viewings", response_model=ViewingRead, status_code=status.HTTP_201_CREATED)
async def request_viewing(
    payload: ViewingRequestCreate,
    user: User = Depends(require_roles(UserRole.HOUSE_SEEKER.value, UserRole.TENANT.value)),
    db: AsyncSession = Depends(get_db),
) -> ViewingRead:
    property_row = await _property_or_404(db, payload.property_id)
    row = ViewingRequest(
        property_id=property_row.id,
        requester_id=user.id,
        status=ViewingStatus.PENDING.value,
        preferred_at=payload.preferred_at,
        message=payload.message,
    )
    db.add(row)
    await db.flush()
    _notify(
        db,
        property_row.owner_id,
        "viewing_requested",
        "New property viewing request",
        f"{user.display_name} requested to view {property_row.title}.",
        viewing_id=str(row.id),
        property_id=str(property_row.id),
    )
    await db.commit()
    await db.refresh(row)
    return await _viewing_read(db, row)


@router.get("/viewings/mine", response_model=list[ViewingRead])
async def list_my_viewings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ViewingRead]:
    rows = await db.scalars(
        select(ViewingRequest)
        .where(ViewingRequest.requester_id == user.id)
        .order_by(ViewingRequest.created_at.desc())
    )
    return [await _viewing_read(db, row) for row in rows]


@router.get("/viewings/landlord", response_model=list[ViewingRead])
async def list_landlord_viewings(
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> list[ViewingRead]:
    query = select(ViewingRequest).join(Property, Property.id == ViewingRequest.property_id)
    if user.role == UserRole.LANDLORD.value:
        query = query.where(Property.owner_id == user.id)
    rows = await db.scalars(query.order_by(ViewingRequest.created_at.desc()))
    return [await _viewing_read(db, row) for row in rows]


@router.post("/viewings/{viewing_id}/decision", response_model=ViewingRead)
async def decide_viewing(
    viewing_id: uuid.UUID,
    payload: ViewingDecision,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> ViewingRead:
    row = await db.scalar(
        select(ViewingRequest).where(ViewingRequest.id == viewing_id).with_for_update()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viewing request not found")
    property_row = await db.get(Property, row.property_id)
    if property_row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Viewing property is missing")
    if user.role != UserRole.ADMIN.value and property_row.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewing request access denied")
    if row.status not in {ViewingStatus.PENDING.value, ViewingStatus.RESCHEDULED.value}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Viewing request is already finalized")

    scheduled_at = payload.scheduled_at
    if scheduled_at is not None and scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    if scheduled_at is not None and scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Viewing time must be in the future")

    row.status = payload.status
    row.scheduled_at = scheduled_at
    row.response_note = payload.note
    if payload.status == ViewingStatus.ACCEPTED.value:
        title = "Viewing request accepted"
        body = f"Your viewing for {property_row.title} has been accepted."
    elif payload.status == ViewingStatus.RESCHEDULED.value:
        title = "New viewing time proposed"
        body = f"A new viewing time was proposed for {property_row.title}."
    else:
        title = "Viewing request declined"
        body = f"Your viewing request for {property_row.title} was declined."
    _notify(
        db,
        row.requester_id,
        "viewing_updated",
        title,
        body,
        viewing_id=str(row.id),
        property_id=str(property_row.id),
    )
    await db.commit()
    await db.refresh(row)
    return await _viewing_read(db, row)


@router.post("/viewings/{viewing_id}/cancel", response_model=ViewingRead)
async def cancel_viewing(
    viewing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ViewingRead:
    row = await db.scalar(
        select(ViewingRequest).where(ViewingRequest.id == viewing_id).with_for_update()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viewing request not found")
    if row.requester_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewing request access denied")
    if row.status in {ViewingStatus.DECLINED.value, ViewingStatus.CANCELLED.value}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Viewing request is already closed")
    property_row = await db.get(Property, row.property_id)
    if property_row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Viewing property is missing")
    row.status = ViewingStatus.CANCELLED.value
    _notify(
        db,
        property_row.owner_id,
        "viewing_cancelled",
        "Viewing request cancelled",
        f"{user.display_name} cancelled the viewing request for {property_row.title}.",
        viewing_id=str(row.id),
    )
    await db.commit()
    await db.refresh(row)
    return await _viewing_read(db, row)
