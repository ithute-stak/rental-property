import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TenancyStatus(str, enum.Enum):
    ACTIVE = "active"
    NOTICE_GIVEN = "notice_given"
    ENDED = "ended"


class Tenancy(Base):
    __tablename__ = "tenancies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=TenancyStatus.ACTIVE.value, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    notice_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_move_out: Mapped[date | None] = mapped_column(Date)
    allow_readvertise: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inspection_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
