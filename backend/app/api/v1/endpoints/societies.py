"""Society management endpoints."""

import uuid

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DB, CurrentUser
from app.core.exceptions import NotFoundError, ForbiddenError
from app.models.society import Society, SocietyMembership, MemberRole
from app.models.university import University
from app.schemas.society import (
    CreateSocietyRequest,
    UpdateSocietyRequest,
    SocietyResponse,
    MembershipResponse,
)
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/societies", tags=["Societies"])

DEFAULT_APPROVAL_CHAIN = {
    "steps": [
        {"order": 1, "authority": "Faculty Advisor", "role": "faculty_advisor"},
        {"order": 2, "authority": "Head of Department", "role": "hod"},
        {"order": 3, "authority": "Dean of Students", "role": "dean"},
        {"order": 4, "authority": "Student Affairs Office", "role": "student_affairs"},
    ]
}


@router.post("", status_code=201)
async def create_society(
    body: CreateSocietyRequest, user: CurrentUser, db: DB
) -> SuccessResponse[SocietyResponse]:
    """Create a new society and assign the creator as president."""
    # Verify university exists
    result = await db.execute(
        select(University).where(University.id == body.university_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("University not found")

    society = Society(
        name=body.name,
        university_id=body.university_id,
        department=body.department,
        society_type=body.society_type,
        faculty_advisor_name=body.faculty_advisor_name,
        faculty_advisor_email=body.faculty_advisor_email,
        description=body.description,
        approval_chain=DEFAULT_APPROVAL_CHAIN,
    )
    db.add(society)
    await db.flush()

    # Creator becomes president
    membership = SocietyMembership(
        user_id=user.id, society_id=society.id, role=MemberRole.PRESIDENT
    )
    db.add(membership)
    await db.flush()

    return SuccessResponse(
        data=SocietyResponse.model_validate(society),
        message="Society created successfully",
    )


@router.get("")
async def list_my_societies(
    user: CurrentUser, db: DB
) -> SuccessResponse[list[SocietyResponse]]:
    """List all societies the current user belongs to."""
    result = await db.execute(
        select(Society)
        .join(SocietyMembership, SocietyMembership.society_id == Society.id)
        .where(SocietyMembership.user_id == user.id)
    )
    societies = result.scalars().all()
    return SuccessResponse(
        data=[SocietyResponse.model_validate(s) for s in societies],
        message="Societies retrieved",
    )


@router.get("/{society_id}")
async def get_society(
    society_id: uuid.UUID, user: CurrentUser, db: DB
) -> SuccessResponse[SocietyResponse]:
    """Get a specific society (must be a member)."""
    # Verify membership
    membership = await db.execute(
        select(SocietyMembership).where(
            SocietyMembership.user_id == user.id,
            SocietyMembership.society_id == society_id,
        )
    )
    if not membership.scalars().first():
        raise ForbiddenError("You are not a member of this society")

    result = await db.execute(select(Society).where(Society.id == society_id))
    society = result.scalar_one_or_none()
    if not society:
        raise NotFoundError("Society not found")

    return SuccessResponse(
        data=SocietyResponse.model_validate(society),
        message="Society retrieved",
    )


@router.put("/{society_id}")
async def update_society(
    society_id: uuid.UUID,
    body: UpdateSocietyRequest,
    user: CurrentUser,
    db: DB,
) -> SuccessResponse[SocietyResponse]:
    """Update a society profile. Must be president or admin."""
    # Check membership with appropriate role
    membership = await db.execute(
        select(SocietyMembership).where(
            SocietyMembership.user_id == user.id,
            SocietyMembership.society_id == society_id,
            SocietyMembership.role.in_([MemberRole.PRESIDENT, MemberRole.ADMIN]),
        )
    )
    if not membership.scalars().first():
        raise ForbiddenError("Only the president or admin can update the society")

    result = await db.execute(select(Society).where(Society.id == society_id))
    society = result.scalar_one_or_none()
    if not society:
        raise NotFoundError("Society not found")

    # Apply updates for non-None fields
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(society, field, value)

    await db.flush()
    await db.refresh(society)

    return SuccessResponse(
        data=SocietyResponse.model_validate(society),
        message="Society updated successfully",
    )
