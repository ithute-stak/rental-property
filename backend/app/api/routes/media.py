import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_optional_user, require_roles
from app.core.config import settings
from app.core.database import get_db
from app.core.storage import storage
from app.models.media import PropertyMedia
from app.models.rental import Property, PropertyStatus, Unit, User, UserRole
from app.schemas.media import MediaConfirmRequest, MediaUploadRequest, MediaUploadTarget, PropertyMediaRead

router = APIRouter()


async def _property_or_404(db: AsyncSession, property_id: uuid.UUID) -> Property:
    row = await db.get(Property, property_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return row


def _ensure_owner_or_admin(row: Property, user: User) -> None:
    if row.owner_id != user.id and user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Property access denied")


def _ensure_media_editable(row: Property) -> None:
    if row.status not in {PropertyStatus.DRAFT.value, PropertyStatus.REJECTED.value}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Property media can only be changed while the advert is draft or rejected",
        )


async def _validate_unit(db: AsyncSession, property_id: uuid.UUID, unit_id: uuid.UUID | None) -> None:
    if unit_id is None:
        return
    unit = await db.scalar(select(Unit.id).where(Unit.id == unit_id, Unit.property_id == property_id))
    if unit is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unit does not belong to this property")


def _read(media: PropertyMedia) -> PropertyMediaRead:
    return PropertyMediaRead(
        id=media.id,
        property_id=media.property_id,
        unit_id=media.unit_id,
        content_type=media.content_type,
        sort_order=media.sort_order,
        is_cover=media.is_cover,
        url=storage.public_url(media.object_key),
        created_at=media.created_at,
    )


@router.post("/{property_id}/media/upload-url", response_model=MediaUploadTarget)
async def create_upload_url(
    property_id: uuid.UUID,
    payload: MediaUploadRequest,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> MediaUploadTarget:
    property_row = await _property_or_404(db, property_id)
    _ensure_owner_or_admin(property_row, user)
    _ensure_media_editable(property_row)
    await _validate_unit(db, property_id, payload.unit_id)

    object_key, upload_url = storage.create_property_upload(property_id, payload.content_type)
    return MediaUploadTarget(
        object_key=object_key,
        upload_url=upload_url,
        expires_in_seconds=settings.media_upload_expiry_seconds,
        required_headers={"Content-Type": payload.content_type},
    )


@router.post("/{property_id}/media", response_model=PropertyMediaRead, status_code=status.HTTP_201_CREATED)
async def confirm_upload(
    property_id: uuid.UUID,
    payload: MediaConfirmRequest,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> PropertyMediaRead:
    property_row = await _property_or_404(db, property_id)
    _ensure_owner_or_admin(property_row, user)
    _ensure_media_editable(property_row)
    await _validate_unit(db, property_id, payload.unit_id)

    expected_prefix = f"properties/{property_id}/"
    if not payload.object_key.startswith(expected_prefix):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid property media key")

    if settings.object_storage_verify_uploads:
        exists = await asyncio.to_thread(storage.object_exists, payload.object_key)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The image has not been uploaded to object storage",
            )

    existing = await db.scalar(select(PropertyMedia.id).where(PropertyMedia.object_key == payload.object_key))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Media has already been confirmed")

    media_count = await db.scalar(
        select(func.count(PropertyMedia.id)).where(PropertyMedia.property_id == property_id)
    )
    make_cover = payload.is_cover or not media_count
    if make_cover:
        await db.execute(
            update(PropertyMedia)
            .where(PropertyMedia.property_id == property_id)
            .values(is_cover=False)
        )

    media = PropertyMedia(
        property_id=property_id,
        unit_id=payload.unit_id,
        object_key=payload.object_key,
        content_type=payload.content_type,
        sort_order=payload.sort_order,
        is_cover=make_cover,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return _read(media)


@router.get("/{property_id}/media", response_model=list[PropertyMediaRead])
async def list_media(
    property_id: uuid.UUID,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> list[PropertyMediaRead]:
    property_row = await _property_or_404(db, property_id)
    if property_row.status != PropertyStatus.ACTIVE.value:
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        _ensure_owner_or_admin(property_row, user)

    rows = await db.scalars(
        select(PropertyMedia)
        .where(PropertyMedia.property_id == property_id)
        .order_by(PropertyMedia.is_cover.desc(), PropertyMedia.sort_order, PropertyMedia.created_at)
    )
    return [_read(media) for media in rows]


@router.delete("/{property_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    property_id: uuid.UUID,
    media_id: uuid.UUID,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> None:
    property_row = await _property_or_404(db, property_id)
    _ensure_owner_or_admin(property_row, user)
    _ensure_media_editable(property_row)

    media = await db.scalar(
        select(PropertyMedia).where(PropertyMedia.id == media_id, PropertyMedia.property_id == property_id)
    )
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    await asyncio.to_thread(storage.delete, media.object_key)
    await db.delete(media)
    await db.commit()
