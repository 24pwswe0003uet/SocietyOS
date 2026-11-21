"""Society-related request/response schemas."""

import uuid
from pydantic import BaseModel, Field

from app.models.society import SocietyType, MemberRole


class UniversityResponse(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    country: str

    model_config = {"from_attributes": True}


class CreateSocietyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    university_id: uuid.UUID
    department: str = Field(min_length=1, max_length=255)
    society_type: SocietyType
    faculty_advisor_name: str | None = None
    faculty_advisor_email: str | None = None
    description: str | None = None


class SocietyResponse(BaseModel):
    id: uuid.UUID
    name: str
    university_id: uuid.UUID
    department: str
    society_type: SocietyType
    faculty_advisor_name: str | None
    faculty_advisor_email: str | None
    approval_chain: dict | None
    description: str | None

    model_config = {"from_attributes": True}


class UpdateSocietyRequest(BaseModel):
    """Body for PUT /societies/{id}."""

    name: str | None = None
    department: str | None = None
    society_type: SocietyType | None = None
    faculty_advisor_name: str | None = None
    faculty_advisor_email: str | None = None
    approval_chain: dict | None = None
    description: str | None = None


class MembershipResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    society_id: uuid.UUID
    role: MemberRole

    model_config = {"from_attributes": True}
