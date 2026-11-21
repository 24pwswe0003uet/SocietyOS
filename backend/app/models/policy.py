"""University policy data model — extracted from documents or questionnaire (FR-002)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PolicySourceFormat(str, enum.Enum):
    """How the policy data was originally provided."""

    PDF = "pdf"
    DOCX = "docx"
    URL = "url"
    PROSPECTUS = "prospectus"
    QUESTIONNAIRE = "questionnaire"


class PolicyData(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Extracted university event policy information.

    One record per extraction run. Multiple records may exist for the same
    university (e.g. re-analysis with a newer document).
    """

    __tablename__ = "policy_data"

    # ----- Relationships -----
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # ----- Source metadata -----
    source_format: Mapped[PolicySourceFormat] = mapped_column(
        Enum(PolicySourceFormat, name="policy_source_format_enum"),
        nullable=False,
    )
    source_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    source_page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_text_length: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ----- Extracted policy fields -----
    approval_chain: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Format: {"steps": [{"order": 1, "authority": "...", "role": "...", "notes": "..."}]}

    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    required_documents: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Format: ["Event proposal", "Budget plan", ...]

    sponsorship_rules: Mapped[str | None] = mapped_column(Text, nullable=True)

    prohibitions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Format: ["Alcohol", "Gambling", ...]

    additional_rules: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Format: [{"rule": "...", "source": "Section 5.2"}]

    # ----- Quality indicators -----
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 0.0 = no confidence, 1.0 = fully extracted. < 0.7 triggers human review.

    extraction_warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Format: ["Could not determine lead time", ...]

    source_references: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Format: [{"field": "approval_chain", "source": "Page 42, Section 3.1", "excerpt": "..."}]

    # ----- Verification -----
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ----- Timestamps -----
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
