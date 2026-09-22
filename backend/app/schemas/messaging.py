import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ConversationCreate(BaseModel):
    property_id: uuid.UUID


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty")
        return cleaned


class ConversationRead(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    property_title: str
    other_party_id: uuid.UUID
    other_party_name: str
    last_message: str | None
    last_message_at: datetime | None
    unread_count: int
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    body: str
    created_at: datetime
    read_at: datetime | None
    is_mine: bool
