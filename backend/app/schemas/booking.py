import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BookingHoldRead(BaseModel):
    unit_id: uuid.UUID
    acquired: bool
    expires_in_seconds: int


class BookingCreate(BaseModel):
    unit_id: uuid.UUID
    move_in_date: date


class BookingPaymentSubmit(BaseModel):
    method: Literal["mobile_money", "bank_transfer", "cash", "card"]
    reference: str = Field(min_length=2, max_length=180)


class BookingDecision(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class BookingRead(BaseModel):
    id: uuid.UUID
    unit_id: uuid.UUID
    property_id: uuid.UUID
    property_title: str
    unit_name: str
    seeker_id: uuid.UUID
    status: str
    move_in_date: date
    amount_due: Decimal
    currency: str
    payment_status: str
    payment_method: str | None
    payment_reference: str | None
    payment_due_at: datetime
    created_at: datetime


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notification_type: str
    title: str
    body: str
    payload: dict
    read_at: datetime | None
    created_at: datetime
