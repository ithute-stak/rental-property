import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class TenancyActivateRequest(BaseModel):
    booking_id: uuid.UUID


class TenantNoticeCreate(BaseModel):
    expected_move_out: date
    allow_readvertise: bool = True
    note: str | None = Field(default=None, max_length=1000)


class TenancyRead(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    unit_id: uuid.UUID
    property_id: uuid.UUID
    property_title: str
    unit_name: str
    tenant_id: uuid.UUID
    tenant_name: str
    status: str
    start_date: date
    expected_move_out: date | None
    allow_readvertise: bool
    created_at: datetime
