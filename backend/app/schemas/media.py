import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MediaUploadRequest(BaseModel):
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    unit_id: uuid.UUID | None = None


class MediaUploadTarget(BaseModel):
    object_key: str
    upload_url: str
    expires_in_seconds: int
    required_headers: dict[str, str]


class MediaConfirmRequest(BaseModel):
    object_key: str = Field(min_length=10, max_length=500)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    unit_id: uuid.UUID | None = None
    sort_order: int = Field(default=0, ge=0, le=1000)
    is_cover: bool = False


class PropertyMediaRead(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    unit_id: uuid.UUID | None
    content_type: str
    sort_order: int
    is_cover: bool
    url: str
    created_at: datetime
