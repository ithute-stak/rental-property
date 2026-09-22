import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LandlordProfileUpdate(BaseModel):
    business_name: str | None = Field(default=None, max_length=180)
    physical_address: str = Field(min_length=3, max_length=500)


class LandlordProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str | None
    physical_address: str | None
    verification_status: str
    submitted_at: datetime | None
    verified_at: datetime | None
    rejection_reason: str | None


class LandlordVerificationDecision(BaseModel):
    approved: bool
    reason: str | None = Field(default=None, max_length=1000)
