import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FavouriteRead(BaseModel):
    property_id: uuid.UUID
    title: str
    town: str
    area: str | None
    monthly_rent: Decimal | None
    available_rooms: int
    image_url: str | None
    created_at: datetime


class ViewingRequestCreate(BaseModel):
    property_id: uuid.UUID
    preferred_at: datetime
    message: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_future_time(self):
        value = self.preferred_at
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
            object.__setattr__(self, "preferred_at", value)
        if value <= datetime.now(timezone.utc):
            raise ValueError("Preferred viewing time must be in the future")
        return self


class ViewingDecision(BaseModel):
    status: Literal["accepted", "declined", "rescheduled"]
    scheduled_at: datetime | None = None
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.status in {"accepted", "rescheduled"} and self.scheduled_at is None:
            raise ValueError("scheduled_at is required when accepting or rescheduling a viewing")
        return self


class ViewingRead(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    property_title: str
    requester_id: uuid.UUID
    requester_name: str
    status: str
    preferred_at: datetime
    scheduled_at: datetime | None
    message: str | None
    response_note: str | None
    created_at: datetime
