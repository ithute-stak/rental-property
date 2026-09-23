import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentWebhookReceipt(BaseModel):
    provider_event_id: uuid.UUID
    provider: str
    event_id: str
    duplicate: bool
    processing_status: str
    processing_message: str | None
    received_at: datetime
    processed_at: datetime | None


class PaymentProviderEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    event_id: str
    event_type: str
    provider_transaction_id: str | None
    source_type: str
    source_id: uuid.UUID
    outcome: str
    amount: Decimal | None
    currency: str | None
    occurred_at: datetime | None
    processing_status: str
    processing_message: str | None
    received_at: datetime
    processed_at: datetime | None
    reconciled_at: datetime | None
    reconciled_by: uuid.UUID | None
    resolution_note: str | None


class PaymentProviderResolution(BaseModel):
    note: str = Field(min_length=3, max_length=1000)
