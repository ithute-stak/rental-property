import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PropertyCreate(BaseModel):
    owner_id: uuid.UUID
    title: str = Field(min_length=3, max_length=180)
    description: str = ""
    property_type: str = Field(min_length=2, max_length=40)
    physical_address: str = Field(min_length=3, max_length=500)
    district: str = Field(min_length=2, max_length=100)
    town: str = Field(min_length=2, max_length=100)
    area: str | None = Field(default=None, max_length=120)
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    total_rooms: int = Field(gt=0, le=10000)
    security_level: str = Field(min_length=2, max_length=40)
    security_features: dict[str, bool | str | int] = Field(default_factory=dict)


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str
    property_type: str
    status: str
    physical_address: str
    district: str
    town: str
    area: str | None
    latitude: Decimal
    longitude: Decimal
    total_rooms: int
    security_level: str
    security_features: dict


class UnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    name: str
    monthly_rent: Decimal
    deposit: Decimal
    status: str
    available_from: date | None


class BookingHoldRead(BaseModel):
    unit_id: uuid.UUID
    acquired: bool
    expires_in_seconds: int
