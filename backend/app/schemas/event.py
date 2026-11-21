"""Event-related request/response schemas."""

import uuid
from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.event import EventType, EventStatus


class ParseEventRequest(BaseModel):
    """Body for POST /events/parse — send natural language to Gemini."""

    description: str = Field(min_length=10, max_length=5000)
    society_id: uuid.UUID


class ParsedEventData(BaseModel):
    """Structured data extracted by Gemini from a natural-language description."""

    title: str | None = None
    event_type: EventType | None = None
    description: str | None = None
    audience_size: int | None = None
    event_date: date_type | None = None
    duration_days: int | None = None
    venue_type: str | None = None
    budget_target: Decimal | None = None
    currency: str = "PKR"
    stakeholder_categories: list[str] = []
    additional_requirements: list[str] = []
    clarification_needed: str | None = None


class CreateEventRequest(BaseModel):
    """Body for POST /events — create from reviewed/edited fields."""

    society_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    event_type: EventType
    description: str | None = None
    audience_size: int | None = None
    event_date: date_type | None = None
    duration_days: int = 1
    venue_type: str | None = None
    budget_target: Decimal | None = None
    currency: str = "PKR"
    status: EventStatus = EventStatus.DRAFT


class UpdateEventRequest(BaseModel):
    """Body for PUT /events/{id}."""

    title: str | None = None
    event_type: EventType | None = None
    description: str | None = None
    audience_size: int | None = None
    event_date: date_type | None = None
    duration_days: int | None = None
    venue_type: str | None = None
    budget_target: Decimal | None = None
    currency: str | None = None
    status: EventStatus | None = None


class EventResponse(BaseModel):
    """Public event representation."""

    id: uuid.UUID
    society_id: uuid.UUID
    created_by: uuid.UUID
    title: str
    event_type: EventType
    description: str | None
    audience_size: int | None
    event_date: date_type | None
    duration_days: int
    venue_type: str | None
    budget_target: Decimal | None
    currency: str
    status: EventStatus

    model_config = {"from_attributes": True}
