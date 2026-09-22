import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import PaymentReferenceClaim


class PaymentReferenceConflict(ValueError):
    pass


def normalize_payment_reference(reference: str) -> str:
    return reference.strip().upper()


async def claim_payment_reference(
    db: AsyncSession,
    *,
    method: str,
    reference: str,
    source_type: str,
    source_id: uuid.UUID,
) -> PaymentReferenceClaim:
    normalized_method = method.strip().lower()
    normalized_reference = normalize_payment_reference(reference)

    statement = (
        insert(PaymentReferenceClaim)
        .values(
            method=normalized_method,
            reference=normalized_reference,
            source_type=source_type,
            source_id=source_id,
        )
        .on_conflict_do_nothing(constraint="uq_payment_reference_method_reference")
        .returning(PaymentReferenceClaim.id)
    )
    created_id = await db.scalar(statement)
    if created_id is not None:
        return await db.get(PaymentReferenceClaim, created_id)

    existing = await db.scalar(
        select(PaymentReferenceClaim).where(
            PaymentReferenceClaim.method == normalized_method,
            PaymentReferenceClaim.reference == normalized_reference,
        )
    )
    if existing is None:
        raise RuntimeError("Payment reference claim could not be resolved after conflict")
    if existing.source_type == source_type and existing.source_id == source_id:
        return existing

    raise PaymentReferenceConflict("This payment reference has already been submitted")
