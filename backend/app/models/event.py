"""Event record model."""

import enum
import uuid
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import String, Enum, ForeignKey, Integer, Numeric, Date, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EventType(str, enum.Enum):
    """Types of events a society can organize."""

    HACKATHON = "hackathon"
    WORKSHOP = "workshop"
    CONFERENCE = "conference"
    SEMINAR = "seminar"
    COMPETITION = "competition"
    SPEAKER = "speaker"
    OTHER = "other"


class EventStatus(str, enum.Enum):
    """Lifecycle status of an event."""

    DRAFT = "draft"
    GENERATING = "generating"
    REVIEW = "review"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class EventRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Core event data created from natural-language input."""

    __tablename__ = "event_records"

    society_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("societies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type_enum"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    venue_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    budget_target: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(10), default="PKR", nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status_enum"),
        default=EventStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Relationships
    society = relationship("Society", back_populates="events")
