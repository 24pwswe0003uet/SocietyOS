"""Proposal Generator Agent (FR-003)."""

import logging
from typing import Any

from app.services.agents.base import BaseAgent, EventContext
from app.services.ai.gemini import gemini_provider

logger = logging.getLogger("societyos.agents.proposal")

PROMPT = """You are an expert university event proposal writer for SocietyOS AI.

Write a professional event proposal for the following event:

{context}

Generate a JSON object with these 8 sections. Each section should be 2-4 paragraphs of professional, formal content suitable for university administration review:

{{
  "executive_summary": "Overview of the event and its significance",
  "objectives": "Specific measurable objectives for the event",
  "scope": "What the event covers, target audience, format",
  "schedule": "Proposed timeline and agenda structure",
  "resources": "Required resources: venue, equipment, human resources, materials",
  "expected_outcomes": "Tangible outcomes and impact on the university/society",
  "risk_assessment": "Potential risks and mitigation strategies",
  "appendices": "Additional notes, references, and supporting details"
}}
"""


class ProposalAgent(BaseAgent):
    agent_name = "proposal"

    async def generate(self, context: EventContext) -> dict[str, Any]:
        prompt = PROMPT.format(context=context.full_prompt_context())
        try:
            result = await gemini_provider.generate_structured(
                prompt=prompt,
                schema_description='{"executive_summary":"string","objectives":"string","scope":"string","schedule":"string","resources":"string","expected_outcomes":"string","risk_assessment":"string","appendices":"string"}',
                max_tokens=6000,
            )
            # Ensure all required sections exist
            sections = {}
            for key in ["executive_summary", "objectives", "scope", "schedule", "resources", "expected_outcomes", "risk_assessment", "appendices"]:
                sections[key] = result.get(key, "")
            return {"sections": sections}
        except Exception as e:
            logger.error("Proposal agent failed: %s", e)
            return {"sections": {
                "executive_summary": f"Event proposal for {context.event_title} — a {context.event_type} organized by {context.society_name}.",
                "objectives": "Objectives to be defined.",
                "scope": f"This event targets an audience of {context.audience_size or 'TBD'} participants.",
                "schedule": f"Planned for {context.event_date or 'TBD'}, duration {context.duration_days} day(s).",
                "resources": f"Venue: {context.venue_type or 'TBD'}. Budget: {context.currency} {context.budget_target or 'TBD'}.",
                "expected_outcomes": "Expected outcomes to be defined.",
                "risk_assessment": "Risk assessment to be defined.",
                "appendices": "",
            }}
