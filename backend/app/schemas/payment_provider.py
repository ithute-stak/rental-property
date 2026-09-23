import uuid
from datetime import datetime

from pydantic import BaseModel


class PaymentWebhookReceipt(BaseModel):
    provider_event_id: uuid.UUID
    provider: str
    event_id: str
    duplicate: bool
    processing_status: str
    processing_message: str | None
    received_at: datetime
    processed_at: datetime | None
