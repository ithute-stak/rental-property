import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AdvertChargeQuote(BaseModel):
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    note: str | None = Field(default=None, max_length=1000)
    waive: bool = False


class AdvertChargePaymentSubmit(BaseModel):
    method: Literal["mobile_money", "bank_transfer", "cash", "card"]
    reference: str = Field(min_length=2, max_length=180)


class AdvertChargeDecision(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class AdvertChargeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    amount: Decimal
    currency: str
    status: str
    note: str | None
    payment_method: str | None
    payment_reference: str | None
    payment_submitted_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime


class AdminLandlordReviewItem(BaseModel):
    user_id: uuid.UUID
    display_name: str
    phone: str
    email: str | None
    business_name: str | None
    physical_address: str | None
    submitted_at: datetime | None


class AdminPropertyReviewItem(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    owner_name: str
    owner_phone: str
    title: str
    property_type: str
    status: str
    district: str
    town: str
    area: str | None
    total_rooms: int
    security_level: str
    advert_charge: AdvertChargeRead | None = None
