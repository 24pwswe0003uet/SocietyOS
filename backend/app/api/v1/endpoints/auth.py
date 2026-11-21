"""Authentication endpoints: register, login, refresh, current user."""

import uuid

import jwt
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.dependencies import DB, CurrentUser
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: DB) -> SuccessResponse[TokenResponse]:
    """Register a new user account."""
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise ConflictError("A user with this email already exists")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()

    tokens = TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return SuccessResponse(data=tokens, message="Registration successful")


@router.post("/login")
async def login(body: LoginRequest, db: DB) -> SuccessResponse[TokenResponse]:
    """Authenticate with email and password."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    tokens = TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return SuccessResponse(data=tokens, message="Login successful")


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: DB) -> SuccessResponse[TokenResponse]:
    """Get a new access token using a valid refresh token."""
    try:
        payload = decode_token(body.refresh_token)
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    tokens = TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return SuccessResponse(data=tokens, message="Token refreshed")


@router.get("/me")
async def get_current_user_profile(user: CurrentUser) -> SuccessResponse[UserResponse]:
    """Return the authenticated user's profile."""
    return SuccessResponse(
        data=UserResponse.model_validate(user),
        message="User profile retrieved",
    )
