"""Authentication request/response schemas."""

import uuid
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Body for POST /auth/register."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Body for POST /auth/login."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Body for POST /auth/refresh."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Returned on successful auth."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user representation."""

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_university_admin: bool

    model_config = {"from_attributes": True}
