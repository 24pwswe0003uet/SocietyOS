"""FastAPI dependencies: DB session, current user, role checks."""

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.models.society import SocietyMembership, MemberRole

DB = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DB,
    authorization: str | None = Header(None),
) -> User:
    """Extract and validate the JWT from the Authorization header, return the User."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid token")

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: MemberRole):
    """Dependency factory: check that the current user has one of the allowed roles
    in at least one society. Use for general access gating.
    """

    async def _check(user: CurrentUser, db: DB) -> User:
        result = await db.execute(
            select(SocietyMembership).where(
                SocietyMembership.user_id == user.id,
                SocietyMembership.role.in_(allowed_roles),
            )
        )
        if not result.scalars().first():
            raise ForbiddenError("You do not have the required role")
        return user

    return _check
