"""Event memory model — semantic memory for institutional learning.

Uses pgvector Vector column when available, JSONB fallback when not.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Enum, ForeignKey, Integer, Float, Text, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# Try to import pgvector; fall back to JSONB for the embedding column
try:
    from pgvector.sqlalchemy import Vector
    _EMBEDDING_COLUMN_TYPE = Vector(768)
    HAS_PGVECTOR = True
except ImportError:
    _EMBEDDING_COLUMN_TYPE = JSONB
    HAS_PGVECTOR = False


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    EXCLUDED = "excluded"


class EventMemory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Semantic memory record — embedding + metadata for similarity retrieval."""

    __tablename__ = "event_memories"

    # Links
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_records.id", ondelete="CASCADE"),
        nullable=False, index=True, unique=True,
    )
    outcome_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_outcomes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id"),
        nullable=False, index=True,
    )
    society_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("societies.id"),
        nullable=False, index=True,
    )

    # Structured summary
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    lessons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    risk_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    success_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Metrics snapshot
    budget_variance_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    attendance_variance_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sponsor_conversion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    approval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Vector embedding (pgvector Vector(768) or JSONB fallback)
    embedding: Mapped[list] = mapped_column(
        _EMBEDDING_COLUMN_TYPE, nullable=False,
    )

    # Verification & management
    verification_status: Mapped[str] = mapped_column(
        Enum("unverified", "verified", "disputed", "excluded",
             name="verification_status_enum", create_type=False),
        default="unverified",
        server_default="unverified",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
