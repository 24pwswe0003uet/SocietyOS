"""Event CRUD and natural-language parsing endpoints."""

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.core.dependencies import DB, CurrentUser
from app.core.exceptions import NotFoundError, ForbiddenError
from app.models.event import EventRecord
from app.models.society import Society, SocietyMembership, MemberRole
from app.schemas.event import (
    CreateEventRequest,
    UpdateEventRequest,
    EventResponse,
    ParseEventRequest,
    ParsedEventData,
)
from app.schemas.common import SuccessResponse
from app.services.event_service import parse_event_description

router = APIRouter(prefix="/events", tags=["Events"])


async def _verify_society_member(user_id: uuid.UUID, society_id: uuid.UUID, db):
    """Check that user is a member of the society with event-creation permissions."""
    result = await db.execute(
        select(SocietyMembership).where(
            SocietyMembership.user_id == user_id,
            SocietyMembership.society_id == society_id,
            SocietyMembership.role.in_([
                MemberRole.PRESIDENT,
                MemberRole.ADMIN,
                MemberRole.EVENT_ORGANIZER,
            ]),
        )
    )
    if not result.scalars().first():
        raise ForbiddenError("You don't have permission to manage events for this society")


@router.post("/parse")
async def parse_event(
    body: ParseEventRequest, user: CurrentUser, db: DB
) -> SuccessResponse[ParsedEventData]:
    """Parse a natural-language event description using Gemini AI."""
    await _verify_society_member(user.id, body.society_id, db)

    parsed = await parse_event_description(body.description)
    return SuccessResponse(data=parsed, message="Event parsed successfully")


@router.post("", status_code=201)
async def create_event(
    body: CreateEventRequest, user: CurrentUser, db: DB
) -> SuccessResponse[EventResponse]:
    """Create a new event from reviewed/edited fields."""
    await _verify_society_member(user.id, body.society_id, db)

    # Verify society exists
    result = await db.execute(select(Society).where(Society.id == body.society_id))
    if not result.scalar_one_or_none():
        raise NotFoundError("Society not found")

    event = EventRecord(
        society_id=body.society_id,
        created_by=user.id,
        title=body.title,
        event_type=body.event_type,
        description=body.description,
        audience_size=body.audience_size,
        event_date=body.event_date,
        duration_days=body.duration_days,
        venue_type=body.venue_type,
        budget_target=body.budget_target,
        currency=body.currency,
        status=body.status,
    )
    db.add(event)
    await db.flush()

    return SuccessResponse(
        data=EventResponse.model_validate(event),
        message="Event created successfully",
    )


@router.get("")
async def list_events(
    user: CurrentUser, db: DB, society_id: uuid.UUID | None = None
) -> SuccessResponse[list[EventResponse]]:
    """List events for the user's societies, optionally filtered by society_id."""
    # Get user's society IDs
    membership_result = await db.execute(
        select(SocietyMembership.society_id).where(
            SocietyMembership.user_id == user.id
        )
    )
    my_society_ids = [row[0] for row in membership_result.fetchall()]

    if not my_society_ids:
        return SuccessResponse(data=[], message="No events found")

    query = select(EventRecord).where(EventRecord.society_id.in_(my_society_ids))
    if society_id and society_id in my_society_ids:
        query = query.where(EventRecord.society_id == society_id)

    query = query.order_by(EventRecord.created_at.desc())
    result = await db.execute(query)
    events = result.scalars().all()

    return SuccessResponse(
        data=[EventResponse.model_validate(e) for e in events],
        message="Events retrieved",
    )


@router.get("/{event_id}")
async def get_event(
    event_id: uuid.UUID, user: CurrentUser, db: DB
) -> SuccessResponse[EventResponse]:
    """Get a specific event (must be a society member)."""
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("Event not found")

    # Verify user is a member of the event's society
    membership = await db.execute(
        select(SocietyMembership).where(
            SocietyMembership.user_id == user.id,
            SocietyMembership.society_id == event.society_id,
        )
    )
    if not membership.scalars().first():
        raise ForbiddenError("You are not a member of this event's society")

    return SuccessResponse(
        data=EventResponse.model_validate(event),
        message="Event retrieved",
    )


@router.put("/{event_id}")
async def update_event(
    event_id: uuid.UUID,
    body: UpdateEventRequest,
    user: CurrentUser,
    db: DB,
) -> SuccessResponse[EventResponse]:
    """Update an event's fields."""
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("Event not found")

    await _verify_society_member(user.id, event.society_id, db)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    await db.flush()
    await db.refresh(event)

    return SuccessResponse(
        data=EventResponse.model_validate(event),
        message="Event updated successfully",
    )
