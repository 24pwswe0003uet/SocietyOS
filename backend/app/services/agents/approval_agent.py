"""Approval Workflow Agent (FR-006)."""

import logging
from datetime import date, timedelta
from typing import Any

from app.services.agents.base import BaseAgent, EventContext

logger = logging.getLogger("societyos.agents.approval")


class ApprovalAgent(BaseAgent):
    """Generates approval timeline from society profile + policy data.

    This agent does NOT need Gemini — it's purely logical computation
    from the approval chain, event date, and policy lead times.
    """

    agent_name = "approval"

    async def generate(self, context: EventContext) -> dict[str, Any]:
        event_date_str = context.event_date
        lead_time = context.policy.lead_time_days or 14

        # Parse event date
        try:
            evt_date = date.fromisoformat(event_date_str) if event_date_str else None
        except (ValueError, TypeError):
            evt_date = None

        chain = context.approval_chain
        if not chain:
            chain = [
                {"order": 1, "authority": context.faculty_advisor or "Faculty Advisor", "role": "faculty_advisor"},
                {"order": 2, "authority": "Head of Department", "role": "hod"},
                {"order": 3, "authority": "Dean of Students", "role": "dean"},
                {"order": 4, "authority": "Student Affairs Office", "role": "student_affairs"},
            ]

        # Required documents from policy or defaults
        required_docs = context.policy.required_documents or [
            "Event Proposal", "Budget Plan", "Venue Booking Form"
        ]

        # Build timeline backward from event date
        steps = []
        num_steps = len(chain)
        days_per_step = max(3, lead_time // num_steps)

        warnings = []
        today = date.today()

        for i, step_def in enumerate(chain):
            if evt_date:
                deadline = evt_date - timedelta(days=lead_time - (i * days_per_step))
                if deadline < today:
                    warnings.append(
                        f"Step {i + 1} ({step_def['authority']}) deadline {deadline.isoformat()} "
                        f"is in the past. Timeline is too tight."
                    )
            else:
                deadline = None

            steps.append({
                "step_order": step_def.get("order", i + 1),
                "authority": step_def["authority"],
                "role": step_def.get("role", ""),
                "deadline": deadline.isoformat() if deadline else None,
                "required_documents": required_docs if i == 0 else [],
                "status": "pending",
            })

        # Check if less than 14 days to event
        if evt_date and (evt_date - today).days < 14:
            warnings.append(
                f"Event is in {(evt_date - today).days} days — fewer than 14. "
                f"Consider the fastest possible submission path."
            )

        return {
            "steps": steps,
            "lead_time_days": lead_time,
            "warnings": warnings,
            "total_approval_days": lead_time,
        }
