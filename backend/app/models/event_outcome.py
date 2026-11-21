"""Event outcome model — post-event actuals for institutional memory (Layer 2)."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Enum, ForeignKey, Integer, Numeric, Float, Text, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ApprovalResult(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class EventOutcome(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Post-event outcome record for institutional memory."""

    __tablename__ = "event_outcomes"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_records.id", ondelete="CASCADE"),
        nullable=False, index=True, unique=True,
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id"),
        nullable=False, index=True,
    )
    approval_result: Mapped[ApprovalResult] = mapped_column(
        Enum(ApprovalResult, name="approval_result_enum"), nullable=False,
    )
    rejection_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    actual_approval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_target: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    actual_spend: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    budget_variance_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    overspent_categories: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    expected_audience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_audience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sponsors_pitched: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sponsors_confirmed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # Verification fields (Phase 7)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
