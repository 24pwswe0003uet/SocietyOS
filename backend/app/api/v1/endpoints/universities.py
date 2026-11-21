"""University listing and creation endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import DB, CurrentUser
from app.core.exceptions import ConflictError
from app.models.university import University
from app.schemas.society import UniversityResponse
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/universities", tags=["Universities"])


class CreateUniversityRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    country: str = Field(default="Pakistan", max_length=100)


@router.get("")
async def list_universities(db: DB) -> SuccessResponse[list[UniversityResponse]]:
    """List all registered universities (public endpoint for registration flow)."""
    result = await db.execute(select(University).order_by(University.name))
    universities = result.scalars().all()
    return SuccessResponse(
        data=[UniversityResponse.model_validate(u) for u in universities],
        message="Universities retrieved",
    )


@router.post("", status_code=201)
async def create_university(
    body: CreateUniversityRequest, user: CurrentUser, db: DB,
) -> SuccessResponse[UniversityResponse]:
    """Create a new university record."""
    # Check for duplicate
    existing = await db.execute(select(University).where(University.name == body.name))
    if existing.scalar_one_or_none():
        raise ConflictError("University with this name already exists")

    university = University(name=body.name, city=body.city, country=body.country)
    db.add(university)
    await db.flush()
    return SuccessResponse(
        data=UniversityResponse.model_validate(university),
        message="University created",
    )
