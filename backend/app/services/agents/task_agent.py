"""Task Assignment Agent (FR-007)."""

import logging
from datetime import date, timedelta
from typing import Any

from app.services.agents.base import BaseAgent, EventContext
from app.services.ai.gemini import gemini_provider

logger = logging.getLogger("societyos.agents.task")

PROMPT = """You are an expert event project manager for SocietyOS AI.

Create a task board for the following event:

{context}

Generate tasks across 6 teams: Logistics, Marketing, Sponsorship, Tech, Registration, Day-of Coordination.
Each task should have: title, description, team, suggested role (not a person's name), due_date (YYYY-MM-DD), priority (low/medium/high/urgent), and dependencies (list of task titles this depends on, or empty list).

Today is {today}. Event date is {event_date}.

{{
  "tasks": [
    {{
      "title": "Book venue",
      "description": "Secure the venue and confirm booking",
      "team": "Logistics",
      "assigned_to": "Logistics Lead",
      "due_date": "2027-01-01",
      "priority": "high",
      "dependencies": []
    }}
  ]
}}

Generate 12-20 tasks that realistically cover the full event preparation.
"""


class TaskAgent(BaseAgent):
    agent_name = "task"

    async def generate(self, context: EventContext) -> dict[str, Any]:
        today = date.today()
        evt_date = context.event_date or (today + timedelta(days=30)).isoformat()

        prompt = PROMPT.format(
            context=context.full_prompt_context(),
            today=today.isoformat(),
            event_date=evt_date,
        )
        try:
            result = await gemini_provider.generate_structured(
                prompt=prompt,
                schema_description='{"tasks":[{"title":"string","description":"string","team":"string","assigned_to":"string","due_date":"YYYY-MM-DD","priority":"low|medium|high|urgent","dependencies":["string"]}]}',
                max_tokens=5000,
            )
            return result
        except Exception as e:
            logger.error("Task agent failed: %s", e)
            # Fallback: generate a basic task list
            try:
                evt = date.fromisoformat(evt_date)
            except (ValueError, TypeError):
                evt = today + timedelta(days=30)

            return {"tasks": [
                {"title": "Book venue", "description": "Secure venue booking", "team": "Logistics", "assigned_to": "Logistics Lead", "due_date": (evt - timedelta(days=21)).isoformat(), "priority": "high", "dependencies": []},
                {"title": "Create event poster", "description": "Design promotional materials", "team": "Marketing", "assigned_to": "Marketing Lead", "due_date": (evt - timedelta(days=14)).isoformat(), "priority": "medium", "dependencies": []},
                {"title": "Contact potential sponsors", "description": "Send sponsorship packages", "team": "Sponsorship", "assigned_to": "Sponsorship Lead", "due_date": (evt - timedelta(days=21)).isoformat(), "priority": "high", "dependencies": []},
                {"title": "Set up registration form", "description": "Create and test registration", "team": "Registration", "assigned_to": "Tech Lead", "due_date": (evt - timedelta(days=14)).isoformat(), "priority": "medium", "dependencies": []},
                {"title": "Arrange AV equipment", "description": "Projector, sound system, mics", "team": "Tech", "assigned_to": "Tech Lead", "due_date": (evt - timedelta(days=7)).isoformat(), "priority": "medium", "dependencies": ["Book venue"]},
                {"title": "Order catering", "description": "Food and beverages for attendees", "team": "Logistics", "assigned_to": "Logistics Lead", "due_date": (evt - timedelta(days=7)).isoformat(), "priority": "medium", "dependencies": []},
                {"title": "Print materials", "description": "Banners, badges, certificates", "team": "Marketing", "assigned_to": "Marketing Lead", "due_date": (evt - timedelta(days=3)).isoformat(), "priority": "medium", "dependencies": ["Create event poster"]},
                {"title": "Day-of coordination plan", "description": "Assign roles and timeline for event day", "team": "Day-of Coordination", "assigned_to": "Event Organizer", "due_date": (evt - timedelta(days=2)).isoformat(), "priority": "high", "dependencies": []},
            ]}
