"""Pydantic schemas for event outcomes and memory management."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class OutcomeCreate(BaseModel):
    """Validated input for submitting post-event outcome."""

    approval_result: str = Field(..., pattern="^(approved|rejected|withdrawn)$")
    rejection_reasons: Optional[list[str]] = None
    actual_approval_days: Optional[int] = Field(None, ge=0, le=365)
    actual_spend: Optional[float] = Field(None, ge=0)
    overspent_categories: Optional[list[str]] = None
    actual_audience: Optional[int] = Field(None, ge=0)
    sponsors_pitched: Optional[int] = Field(None, ge=0)
    sponsors_confirmed: Optional[int] = Field(None, ge=0)
    lessons_learned: Optional[str] = Field(None, max_length=5000)
    risk_flags: Optional[list[str]] = None

    @field_validator("rejection_reasons")
    @classmethod
    def validate_rejection_reasons(cls, v, info):
        if info.data.get("approval_result") == "rejected" and not v:
            raise ValueError("rejection_reasons required when approval_result is 'rejected'")
        return v

    @field_validator("sponsors_confirmed")
    @classmethod
    def validate_sponsors_confirmed(cls, v, info):
        pitched = info.data.get("sponsors_pitched")
        if v is not None and pitched is not None and v > pitched:
            raise ValueError("sponsors_confirmed cannot exceed sponsors_pitched")
        return v


class OutcomeUpdate(BaseModel):
    """Partial update for correcting historical outcome data."""

    actual_spend: Optional[float] = Field(None, ge=0)
    overspent_categories: Optional[list[str]] = None
    actual_audience: Optional[int] = Field(None, ge=0)
    sponsors_pitched: Optional[int] = Field(None, ge=0)
    sponsors_confirmed: Optional[int] = Field(None, ge=0)
    lessons_learned: Optional[str] = Field(None, max_length=5000)
    risk_flags: Optional[list[str]] = None


class OutcomeResponse(BaseModel):
    """Outcome data returned to the client."""

    id: str
    event_id: str
    university_id: str
    approval_result: str
    rejection_reasons: Optional[list[str]] = None
    actual_approval_days: Optional[int] = None
    budget_target: Optional[float] = None
    actual_spend: Optional[float] = None
    budget_variance_pct: Optional[float] = None
    overspent_categories: Optional[list[str]] = None
    expected_audience: Optional[int] = None
    actual_audience: Optional[int] = None
    sponsors_pitched: Optional[int] = None
    sponsors_confirmed: Optional[int] = None
    lessons_learned: Optional[str] = None
    risk_flags: Optional[list[str]] = None
    completed_at: Optional[str] = None
    is_verified: bool = False
    verified_at: Optional[str] = None
    created_at: Optional[str] = None


class MemoryResponse(BaseModel):
    """Semantic memory record returned to the client."""

    id: str
    event_id: str
    event_title: str
    event_type: str
    summary_text: str
    lessons: Optional[list[str]] = None
    risk_flags: Optional[list[str]] = None
    success_factors: Optional[list[str]] = None
    budget_variance_pct: Optional[float] = None
    attendance_variance_pct: Optional[float] = None
    sponsor_conversion_rate: Optional[float] = None
    approval_days: Optional[int] = None
    verification_status: str = "unverified"
    is_active: bool = True
    admin_notes: Optional[str] = None
    created_at: Optional[str] = None


class MemoryUpdate(BaseModel):
    """Update memory verification or exclude from retrieval."""

    verification_status: Optional[str] = Field(None, pattern="^(unverified|verified|disputed|excluded)$")
    is_active: Optional[bool] = None
    admin_notes: Optional[str] = Field(None, max_length=2000)
    lessons: Optional[list[str]] = None
