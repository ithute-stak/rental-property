import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.advertising import AdvertCharge, AdvertChargeStatus
from app.models.booking import Notification
from app.models.rental import (
    LandlordProfile,
    Property,
    PropertyStatus,
    User,
    UserRole,
    VerificationStatus,
)
from app.schemas.advertising import (
    AdminLandlordReviewItem,
    AdminPropertyReviewItem,
    AdvertChargeDecision,
    AdvertChargeQuote,
    AdvertChargeRead,
)
from app.schemas.landlord import LandlordProfileRead, LandlordVerificationDecision
from app.schemas.property import PropertyRead

router = APIRouter()


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


@router.get("/landlords/pending", response_model=list[AdminLandlordReviewItem])
async def list_pending_landlord_verifications(
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> list[AdminLandlordReviewItem]:
    rows = await db.execute(
        select(LandlordProfile, User)
        .join(User, User.id == LandlordProfile.user_id)
        .where(LandlordProfile.verification_status == VerificationStatus.PENDING.value)
        .order_by(LandlordProfile.submitted_at)
    )
    return [
        AdminLandlordReviewItem(
            user_id=user.id,
            display_name=user.display_name,
            phone=user.phone,
            email=user.email,
            business_name=profile.business_name,
            physical_address=profile.physical_address,
            submitted_at=profile.submitted_at,
        )
        for profile, user in rows.all()
    ]


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
        _notify(
            db,
            user_id,
            "landlord_verification_approved",
            "Landlord verification approved",
            "Mosala Rentals approved your landlord profile. You can now submit rental adverts for review.",
        )
    else:
        profile.verification_status = VerificationStatus.REJECTED.value
        profile.verified_at = None
        profile.rejection_reason = payload.reason or "Verification was not approved"
        _notify(
            db,
            user_id,
            "landlord_verification_rejected",
            "Landlord verification needs changes",
            profile.rejection_reason,
        )

    await db.commit()
    await db.refresh(profile)
    return profile


async def _property(db: AsyncSession, property_id: uuid.UUID) -> Property:
    row = await db.get(Property, property_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return row


@router.get("/properties/review", response_model=list[AdminPropertyReviewItem])
async def list_property_review_queue(
    review_status: str = Query(default=PropertyStatus.PENDING_VERIFICATION.value),
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> list[AdminPropertyReviewItem]:
    allowed = {
        PropertyStatus.PENDING_VERIFICATION.value,
        PropertyStatus.APPROVED.value,
        PropertyStatus.REJECTED.value,
        PropertyStatus.ACTIVE.value,
    }
    if review_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported property review status",
        )

    rows = await db.execute(
        select(Property, User)
        .join(User, User.id == Property.owner_id)
        .where(Property.status == review_status)
        .order_by(Property.created_at)
    )
    result: list[AdminPropertyReviewItem] = []
    for property_row, owner in rows.all():
        charge = await db.scalar(
            select(AdvertCharge).where(AdvertCharge.property_id == property_row.id)
        )
        result.append(
            AdminPropertyReviewItem(
                id=property_row.id,
                owner_id=owner.id,
                owner_name=owner.display_name,
                owner_phone=owner.phone,
                title=property_row.title,
                property_type=property_row.property_type,
                status=property_row.status,
                district=property_row.district,
                town=property_row.town,
                area=property_row.area,
                total_rooms=property_row.total_rooms,
                security_level=property_row.security_level,
                advert_charge=AdvertChargeRead.model_validate(charge) if charge else None,
            )
        )
    return result


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
    _notify(
        db,
        row.owner_id,
        "property_approved",
        "Rental advert approved",
        f"{row.title} passed Mosala property review. The advertising charge can now be issued.",
        property_id=str(row.id),
    )
    await db.commit()
    await db.refresh(row)
    return row


@router.put("/properties/{property_id}/charge", response_model=AdvertChargeRead)
async def quote_advert_charge(
    property_id: uuid.UUID,
    payload: AdvertChargeQuote,
    admin: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> AdvertCharge:
    row = await _property(db, property_id)
    if row.status != PropertyStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approve the property before quoting an advertising charge",
        )
    if not payload.waive and payload.amount <= Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A payable advertising charge must be greater than zero",
        )

    charge = await db.scalar(
        select(AdvertCharge).where(AdvertCharge.property_id == property_id).with_for_update()
    )
    if charge is not None and charge.status in {
        AdvertChargeStatus.PAID.value,
        AdvertChargeStatus.WAIVED.value,
        AdvertChargeStatus.PAYMENT_SUBMITTED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This advertising charge can no longer be changed",
        )

    now = datetime.now(timezone.utc)
    next_status = AdvertChargeStatus.WAIVED.value if payload.waive else AdvertChargeStatus.QUOTED.value
    amount = Decimal("0") if payload.waive else payload.amount
    if charge is None:
        charge = AdvertCharge(
            property_id=property_id,
            amount=amount,
            currency="LSL",
            status=next_status,
            note=payload.note,
            quoted_by=admin.id,
            confirmed_by=admin.id if payload.waive else None,
            confirmed_at=now if payload.waive else None,
        )
        db.add(charge)
    else:
        charge.amount = amount
        charge.status = next_status
        charge.note = payload.note
        charge.quoted_by = admin.id
        charge.payment_method = None
        charge.payment_reference = None
        charge.payment_submitted_at = None
        charge.confirmed_by = admin.id if payload.waive else None
        charge.confirmed_at = now if payload.waive else None

    message = (
        f"Mosala waived the advertising charge for {row.title}."
        if payload.waive
        else f"Mosala set the advertising charge for {row.title} at M {amount:.2f}."
    )
    _notify(
        db,
        row.owner_id,
        "advert_charge_quoted",
        "Advertising charge updated",
        message,
        property_id=str(row.id),
    )
    await db.commit()
    await db.refresh(charge)
    return charge


@router.post("/properties/{property_id}/charge/confirm", response_model=AdvertChargeRead)
async def confirm_advert_charge_payment(
    property_id: uuid.UUID,
    payload: AdvertChargeDecision,
    admin: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> AdvertCharge:
    row = await _property(db, property_id)
    charge = await db.scalar(
        select(AdvertCharge).where(AdvertCharge.property_id == property_id).with_for_update()
    )
    if charge is None or charge.status != AdvertChargeStatus.PAYMENT_SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Advertising payment is not awaiting verification",
        )
    charge.status = AdvertChargeStatus.PAID.value
    charge.confirmed_by = admin.id
    charge.confirmed_at = datetime.now(timezone.utc)
    if payload.note:
        charge.note = payload.note
    _notify(
        db,
        row.owner_id,
        "advert_charge_paid",
        "Advertising payment confirmed",
        f"Mosala verified the advertising payment for {row.title}. The advert is ready for activation.",
        property_id=str(row.id),
    )
    await db.commit()
    await db.refresh(charge)
    return charge


@router.post("/properties/{property_id}/charge/reject", response_model=AdvertChargeRead)
async def reject_advert_charge_payment(
    property_id: uuid.UUID,
    payload: AdvertChargeDecision,
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> AdvertCharge:
    row = await _property(db, property_id)
    charge = await db.scalar(
        select(AdvertCharge).where(AdvertCharge.property_id == property_id).with_for_update()
    )
    if charge is None or charge.status != AdvertChargeStatus.PAYMENT_SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Advertising payment is not awaiting verification",
        )
    charge.status = AdvertChargeStatus.PAYMENT_REJECTED.value
    charge.note = payload.note or "The advertising payment reference could not be verified"
    _notify(
        db,
        row.owner_id,
        "advert_charge_payment_rejected",
        "Advertising payment needs attention",
        charge.note,
        property_id=str(row.id),
    )
    await db.commit()
    await db.refresh(charge)
    return charge


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
    charge = await db.scalar(select(AdvertCharge).where(AdvertCharge.property_id == property_id))
    if charge is None or charge.status not in {
        AdvertChargeStatus.PAID.value,
        AdvertChargeStatus.WAIVED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Advertising charge must be paid or waived before activation",
        )
    row.status = PropertyStatus.ACTIVE.value
    _notify(
        db,
        row.owner_id,
        "property_activated",
        "Rental advert is live",
        f"{row.title} is now active on the Mosala Rentals marketplace.",
        property_id=str(row.id),
    )
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
    _notify(
        db,
        row.owner_id,
        "property_rejected",
        "Rental advert needs changes",
        f"{row.title} was returned for changes before it can be advertised.",
        property_id=str(row.id),
    )
    await db.commit()
    await db.refresh(row)
    return row
