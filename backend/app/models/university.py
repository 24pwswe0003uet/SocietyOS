"""University model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class University(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A registered university."""

    __tablename__ = "universities"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="Pakistan", nullable=False)

    # Relationships
    societies = relationship("Society", back_populates="university", lazy="selectin")
