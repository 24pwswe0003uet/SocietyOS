"""Policy-related request/response schemas for FR-002."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.policy import PolicySourceFormat


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class QuestionnaireRequest(BaseModel):
    """Mode 3: Five-question fallback from the PRD."""

    university_id: uuid.UUID | None = None
    event_id: uuid.UUID | None = None
    faculty_advisor: str = Field(default="", description="Name of faculty advisor")
    department: str = Field(default="", description="Society's department")
    reports_to: str = Field(
        default="academic",
        description="'student_affairs' or 'academic'",
        pattern=r"^(student_affairs|academic)$",
    )
    previous_events: str = Field(
        default="",
        description="Past event experience and submission timing",
    )
    past_rejections: str = Field(
        default="",
        description="Any past rejections and reasons",
    )


class VerifyPolicyRequest(BaseModel):
    """Human verification: confirm or correct extracted policy fields."""

    approval_chain: dict | None = None
    lead_time_days: int | None = None
    required_documents: list[str] | None = None
    sponsorship_rules: str | None = None
    prohibitions: list[str] | None = None
    additional_rules: list[dict] | None = None
    verification_notes: str | None = None


class UpdatePolicyFieldRequest(BaseModel):
    """Edit a single field on a policy record."""

    field: str = Field(description="Field name to update")
    value: str | int | float | list | dict | None = Field(description="New value")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ApprovalStepSchema(BaseModel):
    order: int
    authority: str
    role: str
    notes: str | None = None


class SourceReferenceSchema(BaseModel):
    field: str | None = None
    source: str
    excerpt: str | None = None


class PolicyDataResponse(BaseModel):
    """Full policy data response — same structure for all 3 input modes."""

    id: uuid.UUID
    university_id: uuid.UUID
    event_id: uuid.UUID | None
    created_by: uuid.UUID | None
    source_format: PolicySourceFormat
    source_filename: str | None
    source_url: str | None
    source_page_count: int | None
    source_text_length: int | None

    # Extracted fields
    approval_chain: dict | None
    lead_time_days: int | None
    required_documents: list | None
    sponsorship_rules: str | None
    prohibitions: list | None
    additional_rules: list | None

    # Quality
    confidence_score: float | None
    extraction_warnings: list | None
    source_references: list | None

    # Verification
    is_verified: bool
    verified_by: uuid.UUID | None
    verified_at: datetime | None
    verification_notes: str | None

    # Timestamps
    extracted_at: datetime
    created_at: datetime

    # Computed helpers for the frontend
    needs_review: bool = False

    model_config = {"from_attributes": True}

    def model_post_init(self, __context) -> None:
        """Flag records with low confidence for human review."""
        if self.confidence_score is not None and self.confidence_score < 0.7:
            self.needs_review = True


class PolicyListItem(BaseModel):
    """Lightweight policy item for list views."""

    id: uuid.UUID
    source_format: PolicySourceFormat
    source_filename: str | None
    confidence_score: float | None
    is_verified: bool
    extracted_at: datetime
    needs_review: bool = False

    model_config = {"from_attributes": True}

    def model_post_init(self, __context) -> None:
        if self.confidence_score is not None and self.confidence_score < 0.7:
            self.needs_review = True
