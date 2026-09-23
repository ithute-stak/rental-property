from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.payment_provider import PaymentWebhookReceipt
from app.services.payment_providers import (
    PaymentWebhookConflict,
    PaymentWebhookPayloadError,
    PaymentWebhookSignatureError,
    ingest_payment_webhook,
)

router = APIRouter()
MAX_WEBHOOK_BODY_BYTES = 64 * 1024


async def _bounded_body(request: Request) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_WEBHOOK_BODY_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Payment webhook payload is too large",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/webhooks/{provider}", response_model=PaymentWebhookReceipt)
async def receive_payment_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PaymentWebhookReceipt:
    body = await _bounded_body(request)
    try:
        result = await ingest_payment_webhook(
            db,
            provider=provider,
            body=body,
            headers=request.headers,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment provider is not configured",
        ) from exc
    except PaymentWebhookSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Payment webhook signature is invalid",
        ) from exc
    except PaymentWebhookPayloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PaymentWebhookConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    await db.commit()
    event = result.event
    return PaymentWebhookReceipt(
        provider_event_id=event.id,
        provider=event.provider,
        event_id=event.event_id,
        duplicate=result.duplicate,
        processing_status=event.processing_status,
        processing_message=event.processing_message,
        received_at=event.received_at,
        processed_at=event.processed_at,
    )
