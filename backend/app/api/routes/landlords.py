from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.rental import LandlordProfile, User, UserRole, VerificationStatus
from app.schemas.landlord import LandlordProfileRead, LandlordProfileUpdate

router = APIRouter()


async def _profile_for_user(db: AsyncSession, user_id) -> LandlordProfile:
    profile = await db.scalar(select(LandlordProfile).where(LandlordProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landlord profile not found",
        )
    return profile


@router.get("/me", response_model=LandlordProfileRead)
async def get_my_landlord_profile(
    user: User = Depends(require_roles(UserRole.LANDLORD.value)),
    db: AsyncSession = Depends(get_db),
) -> LandlordProfile:
    return await _profile_for_user(db, user.id)


@router.put("/me", response_model=LandlordProfileRead)
async def update_my_landlord_profile(
    payload: LandlordProfileUpdate,
    user: User = Depends(require_roles(UserRole.LANDLORD.value)),
    db: AsyncSession = Depends(get_db),
) -> LandlordProfile:
    profile = await _profile_for_user(db, user.id)
    if profile.verification_status == VerificationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile cannot be changed while verification is pending",
        )

    profile.business_name = payload.business_name.strip() if payload.business_name else None
    profile.physical_address = payload.physical_address.strip()
    if profile.verification_status == VerificationStatus.REJECTED.value:
        profile.verification_status = VerificationStatus.NOT_SUBMITTED.value
        profile.rejection_reason = None

    await db.commit()
    await db.refresh(profile)
    return profile


@router.post("/me/submit", response_model=LandlordProfileRead)
async def submit_landlord_verification(
    user: User = Depends(require_roles(UserRole.LANDLORD.value)),
    db: AsyncSession = Depends(get_db),
) -> LandlordProfile:
    profile = await _profile_for_user(db, user.id)
    if not profile.physical_address:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Complete the landlord profile before submitting it",
        )
    if profile.verification_status == VerificationStatus.APPROVED.value:
        return profile
    if profile.verification_status == VerificationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification is already pending",
        )

    profile.verification_status = VerificationStatus.PENDING.value
    profile.submitted_at = datetime.now(timezone.utc)
    profile.rejection_reason = None
    await db.commit()
    await db.refresh(profile)
    return profile
