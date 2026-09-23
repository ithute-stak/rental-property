import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_roles
from app.core.database import get_db
from app.models.payment import PaymentProviderEvent
from app.models.rental import User, UserRole
from app.schemas.payment_provider import PaymentProviderEventRead, PaymentProviderResolution
from app.services.audit import add_audit_event
from app.services.payment_providers import PaymentWebhookPayloadError, normalize_provider_name

router = APIRouter()

_ALLOWED_PROCESSING_STATUSES = {
    "received",
    "recorded",
    "processed",
    "manual_review",
    "resolved",
}
_ALLOWED_SOURCE_TYPES = {"booking", "advert_charge"}


def _validate_processing_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _ALLOWED_PROCESSING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported provider-event processing status",
        )
    return normalized


def _validate_source_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _ALLOWED_SOURCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported payment source type",
        )
    return normalized


@router.get("/events", response_model=list[PaymentProviderEventRead])
async def list_payment_provider_events(
    processing_status: str = Query(default="manual_review"),
    provider: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentProviderEvent]:
    event_status = _validate_processing_status(processing_status)
    statement = select(PaymentProviderEvent).where(
        PaymentProviderEvent.processing_status == event_status
    )

    if provider is not None:
        try:
            normalized_provider = normalize_provider_name(provider)
        except PaymentWebhookPayloadError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        statement = statement.where(PaymentProviderEvent.provider == normalized_provider)

    if source_type is not None:
        statement = statement.where(
            PaymentProviderEvent.source_type == _validate_source_type(source_type)
        )
    if source_id is not None:
        statement = statement.where(PaymentProviderEvent.source_id == source_id)

    rows = await db.scalars(
        statement.order_by(PaymentProviderEvent.received_at.desc()).offset(offset).limit(limit)
    )
    return list(rows.all())


@router.get("/events/{event_id}", response_model=PaymentProviderEventRead)
async def get_payment_provider_event(
    event_id: uuid.UUID,
    _: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> PaymentProviderEvent:
    row = await db.get(PaymentProviderEvent, event_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment provider event not found",
        )
    return row


@router.post("/events/{event_id}/resolve", response_model=PaymentProviderEventRead)
async def resolve_payment_provider_event(
    event_id: uuid.UUID,
    payload: PaymentProviderResolution,
    admin: User = Depends(require_roles(UserRole.ADMIN.value)),
    db: AsyncSession = Depends(get_db),
) -> PaymentProviderEvent:
    row = await db.scalar(
        select(PaymentProviderEvent)
        .where(PaymentProviderEvent.id == event_id)
        .with_for_update()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment provider event not found",
        )
    if row.processing_status != "manual_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only provider events awaiting manual review can be resolved",
        )

    previous_status = row.processing_status
    row.processing_status = "resolved"
    row.resolution_note = payload.note.strip()
    row.reconciled_at = datetime.now(timezone.utc)
    row.reconciled_by = admin.id

    add_audit_event(
        db,
        actor=admin,
        action="payment_provider.reconciliation_resolved",
        entity_type="payment_provider_event",
        entity_id=row.id,
        details={
            "provider": row.provider,
            "provider_event_id": row.event_id,
            "source_type": row.source_type,
            "source_id": row.source_id,
            "outcome": row.outcome,
            "from_status": previous_status,
            "to_status": row.processing_status,
            "resolution_note": row.resolution_note,
        },
    )

    await db.commit()
    await db.refresh(row)
    return row
