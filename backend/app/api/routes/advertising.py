import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.advertising import AdvertCharge, AdvertChargeStatus
from app.models.booking import Notification
from app.models.rental import Property, User, UserRole
from app.schemas.advertising import AdvertChargePaymentSubmit, AdvertChargeRead
from app.services.payments import (
    PaymentReferenceConflict,
    claim_payment_reference,
    normalize_payment_reference,
)

router = APIRouter()


async def _owned_property(
    db: AsyncSession,
    property_id: uuid.UUID,
    user: User,
) -> Property:
    row = await db.get(Property, property_id)
    if row is None or (row.owner_id != user.id and user.role != UserRole.ADMIN.value):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return row


@router.get("/properties/{property_id}/charge", response_model=AdvertChargeRead)
async def get_advert_charge(
    property_id: uuid.UUID,
    user: User = Depends(require_roles(UserRole.LANDLORD.value, UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> AdvertCharge:
    await _owned_property(db, property_id, user)
    charge = await db.scalar(select(AdvertCharge).where(AdvertCharge.property_id == property_id))
    if charge is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advert charge has not been quoted yet",
        )
    return charge


@router.post("/properties/{property_id}/charge/payment", response_model=AdvertChargeRead)
async def submit_advert_charge_payment(
    property_id: uuid.UUID,
    payload: AdvertChargePaymentSubmit,
    user: User = Depends(require_roles(UserRole.LANDLORD.value)),
    db: AsyncSession = Depends(get_db),
) -> AdvertCharge:
    property_row = await _owned_property(db, property_id, user)
    charge = await db.scalar(
        select(AdvertCharge).where(AdvertCharge.property_id == property_id).with_for_update()
    )
    if charge is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advert charge has not been quoted yet",
        )
    if charge.status not in {
        AdvertChargeStatus.QUOTED.value,
        AdvertChargeStatus.PAYMENT_REJECTED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Advert charge is not awaiting a payment reference",
        )
    if charge.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This advert charge does not require payment",
        )

    reference = normalize_payment_reference(payload.reference)
    try:
        await claim_payment_reference(
            db,
            method=payload.method,
            reference=reference,
            source_type="advert_charge",
            source_id=charge.id,
        )
    except PaymentReferenceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    charge.payment_method = payload.method
    charge.payment_reference = reference
    charge.payment_submitted_at = datetime.now(timezone.utc)
    charge.status = AdvertChargeStatus.PAYMENT_SUBMITTED.value

    admins = await db.scalars(
        select(User).where(User.role == UserRole.ADMIN.value, User.is_active.is_(True))
    )
    for admin in admins:
        db.add(
            Notification(
                user_id=admin.id,
                notification_type="advert_charge_payment_review",
                title="Advert charge payment needs review",
                body=(
                    f"{property_row.title} submitted advert payment reference "
                    f"{charge.payment_reference}."
                ),
                payload={
                    "property_id": str(property_row.id),
                    "advert_charge_id": str(charge.id),
                },
            )
        )

    await db.commit()
    await db.refresh(charge)
    return charge
