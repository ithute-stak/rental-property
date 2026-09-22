import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.rental import (
    LandlordProfile,
    Property,
    PropertyStatus,
    User,
    UserRole,
    VerificationStatus,
)
from app.schemas.landlord import LandlordProfileRead, LandlordVerificationDecision
from app.schemas.property import PropertyRead

router = APIRouter()


@router.patch("/landlords/{user_id}/verification", response_model=LandlordProfileRead)
async def decide_landlord_verification(
    user_id: uuid.UUID,
    payload: LandlordVerificationDecision,
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> LandlordProfile:
    profile = await db.scalar(select(LandlordProfile).where(LandlordProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landlord profile not found")
    if profile.verification_status != VerificationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending landlord verifications can be reviewed",
        )

    if payload.approved:
        profile.verification_status = VerificationStatus.APPROVED.value
        profile.verified_at = datetime.now(timezone.utc)
        profile.rejection_reason = None
    else:
        profile.verification_status = VerificationStatus.REJECTED.value
        profile.verified_at = None
        profile.rejection_reason = payload.reason or "Verification was not approved"

    await db.commit()
    await db.refresh(profile)
    return profile


async def _property(db: AsyncSession, property_id: uuid.UUID) -> Property:
    row = await db.get(Property, property_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return row


@router.post("/properties/{property_id}/approve", response_model=PropertyRead)
async def approve_property(
    property_id: uuid.UUID,
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> Property:
    row = await _property(db, property_id)
    if row.status != PropertyStatus.PENDING_VERIFICATION.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending properties can be approved",
        )
    row.status = PropertyStatus.APPROVED.value
    await db.commit()
    await db.refresh(row)
    return row


@router.post("/properties/{property_id}/activate", response_model=PropertyRead)
async def activate_property(
    property_id: uuid.UUID,
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> Property:
    row = await _property(db, property_id)
    if row.status != PropertyStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Property must be approved before activation",
        )
    row.status = PropertyStatus.ACTIVE.value
    await db.commit()
    await db.refresh(row)
    return row


@router.post("/properties/{property_id}/reject", response_model=PropertyRead)
async def reject_property(
    property_id: uuid.UUID,
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> Property:
    row = await _property(db, property_id)
    if row.status not in {
        PropertyStatus.PENDING_VERIFICATION.value,
        PropertyStatus.APPROVED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Property is not in a reviewable state",
        )
    row.status = PropertyStatus.REJECTED.value
    await db.commit()
    await db.refresh(row)
    return row
