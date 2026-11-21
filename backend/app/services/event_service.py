"""Event creation service — NL parsing via Gemini + CRUD operations."""

import json
import logging
from datetime import date, timedelta
from typing import Any

from app.services.ai.gemini import gemini_provider
from app.schemas.event import ParsedEventData

logger = logging.getLogger("societyos.event_service")

EVENT_PARSE_PROMPT = """You are SocietyOS AI, an event planning assistant for university student societies.

A society member has described an event they want to organize. Extract structured information from their description.

Event description:
\"\"\"{description}\"\"\"

Today's date is {today}.

Extract the following fields. Use null for any field you cannot determine from the description.
Do NOT invent information that is not in the description.
If the user says "next month", calculate the approximate date from today.
If the user says "next week", calculate accordingly.
For budget, extract the numeric value and currency (default PKR if not specified).

Required JSON schema:
{{
  "title": "string - a concise event title",
  "event_type": "one of: hackathon, workshop, conference, seminar, competition, speaker, other",
  "description": "string - a 1-2 sentence summary of the event",
  "audience_size": "integer or null",
  "event_date": "YYYY-MM-DD format or null",
  "duration_days": "integer, default 1",
  "venue_type": "string describing venue needs or null",
  "budget_target": "number or null (no currency symbol)",
  "currency": "string, default PKR",
  "stakeholder_categories": ["list of stakeholder groups involved"],
  "additional_requirements": ["list of any special requirements mentioned"],
  "clarification_needed": "string describing what critical info is missing, or null if everything is clear"
}}

If the description is too vague to extract even a title and event_type, set clarification_needed to explain what you need.
"""

EVENT_PARSE_SCHEMA = """{
  "title": "string",
  "event_type": "hackathon|workshop|conference|seminar|competition|speaker|other",
  "description": "string|null",
  "audience_size": "integer|null",
  "event_date": "YYYY-MM-DD|null",
  "duration_days": "integer",
  "venue_type": "string|null",
  "budget_target": "number|null",
  "currency": "string",
  "stakeholder_categories": ["string"],
  "additional_requirements": ["string"],
  "clarification_needed": "string|null"
}"""


async def parse_event_description(description: str) -> ParsedEventData:
    """Use Gemini to extract structured event data from natural language."""
    today = date.today().isoformat()
    prompt = EVENT_PARSE_PROMPT.format(description=description, today=today)

    try:
        raw: dict[str, Any] = await gemini_provider.generate_structured(
            prompt=prompt,
            schema_description=EVENT_PARSE_SCHEMA,
        )
    except Exception as e:
        logger.error("Gemini parsing failed: %s", e)
        # Return minimal parsed data with clarification request
        return ParsedEventData(
            clarification_needed=(
                "AI parsing is currently unavailable. "
                "Please fill in the event details manually."
            )
        )

    # Validate event_type
    valid_types = {"hackathon", "workshop", "conference", "seminar", "competition", "speaker", "other"}
    if raw.get("event_type") and raw["event_type"] not in valid_types:
        raw["event_type"] = "other"

    # Clamp audience_size to reasonable range
    if raw.get("audience_size") and (raw["audience_size"] < 1 or raw["audience_size"] > 100000):
        raw["audience_size"] = None

    # Validate date format
    if raw.get("event_date"):
        try:
            date.fromisoformat(raw["event_date"])
        except (ValueError, TypeError):
            raw["event_date"] = None

    return ParsedEventData(**{
        k: v for k, v in raw.items()
        if k in ParsedEventData.model_fields
    })
