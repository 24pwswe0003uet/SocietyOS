"""Society and membership models."""

import enum
import uuid

from sqlalchemy import String, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SocietyType(str, enum.Enum):
    """Society classification."""

    TECHNICAL = "technical"
    CULTURAL = "cultural"
    PROFESSIONAL = "professional"


class MemberRole(str, enum.Enum):
    """Roles a user can hold within a society."""

    PRESIDENT = "president"
    ADMIN = "admin"
    EVENT_ORGANIZER = "event_organizer"
    SPONSORSHIP_LEAD = "sponsorship_lead"
    FACULTY_ADVISOR = "faculty_advisor"
    MEMBER = "member"


class Society(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A university student society."""

    __tablename__ = "societies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id"), nullable=False, index=True
    )
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    society_type: Mapped[SocietyType] = mapped_column(
        Enum(SocietyType, name="society_type_enum"), nullable=False
    )
    faculty_advisor_name: Mapped[str] = mapped_column(String(255), nullable=True)
    faculty_advisor_email: Mapped[str] = mapped_column(String(255), nullable=True)
    approval_chain: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    university = relationship("University", back_populates="societies")
    memberships = relationship(
        "SocietyMembership", back_populates="society", lazy="selectin"
    )
    events = relationship("EventRecord", back_populates="society", lazy="noload")


class SocietyMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Links a user to a society with a specific role. A user may have many."""

    __tablename__ = "society_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "society_id", "role", name="uq_user_society_role"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    society_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("societies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, name="member_role_enum"), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="memberships")
    society = relationship("Society", back_populates="memberships")
