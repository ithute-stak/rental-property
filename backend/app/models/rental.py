import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from geoalchemy2 import Geography
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    HOUSE_SEEKER = "house_seeker"
    TENANT = "tenant"
    LANDLORD = "landlord"
    ADMIN = "admin"


class PropertyStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_VERIFICATION = "pending_verification"
    APPROVED = "approved"
    ACTIVE = "active"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class UnitStatus(str, enum.Enum):
    AVAILABLE = "available"
    BOOKING_PENDING = "booking_pending"
    BOOKED = "booked"
    OCCUPIED = "occupied"
    NOTICE_GIVEN = "notice_given"
    VACATING_SOON = "vacating_soon"
    INSPECTION = "inspection"
    INACTIVE = "inactive"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    properties: Mapped[list["Property"]] = relationship(back_populates="owner")


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (CheckConstraint("total_rooms > 0", name="ck_properties_total_rooms_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    property_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=PropertyStatus.DRAFT.value, index=True)
    physical_address: Mapped[str] = mapped_column(String(500), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    town: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    area: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    location: Mapped[object] = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    total_rooms: Mapped[int] = mapped_column(nullable=False)
    security_level: Mapped[str] = mapped_column(String(40), nullable=False)
    security_features: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="properties")
    units: Mapped[list["Unit"]] = relationship(back_populates="property", cascade="all, delete-orphan")


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        CheckConstraint("monthly_rent >= 0", name="ck_units_monthly_rent_nonnegative"),
        CheckConstraint("deposit >= 0", name="ck_units_deposit_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    monthly_rent: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deposit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=UnitStatus.AVAILABLE.value, index=True)
    available_from: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    property: Mapped[Property] = relationship(back_populates="units")
