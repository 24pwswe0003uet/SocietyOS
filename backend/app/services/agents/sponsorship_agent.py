"""Sponsorship Agent (FR-005)."""

import logging
from typing import Any

from app.services.agents.base import BaseAgent, EventContext
from app.services.ai.gemini import gemini_provider

logger = logging.getLogger("societyos.agents.sponsorship")

PROMPT = """You are an expert university event sponsorship strategist for SocietyOS AI.

Create a professional sponsorship package for the following event:

{context}

Generate a JSON object with:
1. Three sponsorship tiers (Gold, Silver, Bronze) with realistic amounts in {currency}
2. An audience demographics summary
3. Three personalized outreach email drafts for different industries (tech, FMCG, finance)
   Each email should have 2 subject line variants for A/B testing.

{{
  "tiers": [
    {{
      "name": "Gold",
      "amount": 200000,
      "benefits": ["Logo on main banner", "5-min speaking slot", "Booth space", ...]
    }},
    {{
      "name": "Silver",
      "amount": 100000,
      "benefits": [...]
    }},
    {{
      "name": "Bronze",
      "amount": 50000,
      "benefits": [...]
    }}
  ],
  "audience_summary": "Description of audience demographics and reach",
  "email_drafts": [
    {{
      "industry": "tech",
      "subject_a": "Subject line variant A",
      "subject_b": "Subject line variant B",
      "body": "Full email body"
    }}
  ]
}}
"""


class SponsorshipAgent(BaseAgent):
    agent_name = "sponsorship"

    async def generate(self, context: EventContext) -> dict[str, Any]:
        prompt = PROMPT.format(context=context.full_prompt_context(), currency=context.currency)
        try:
            return await gemini_provider.generate_structured(
                prompt=prompt,
                schema_description='{"tiers":[{"name":"string","amount":"number","benefits":["string"]}],"audience_summary":"string","email_drafts":[{"industry":"string","subject_a":"string","subject_b":"string","body":"string"}]}',
                max_tokens=5000,
            )
        except Exception as e:
            logger.error("Sponsorship agent failed: %s", e)
            budget = float(context.budget_target) if context.budget_target else 300000
            return {
                "tiers": [
                    {"name": "Gold", "amount": budget * 0.4, "benefits": ["Logo on main banner", "Speaking slot", "Premium booth", "Social media mentions", "Post-event report"]},
                    {"name": "Silver", "amount": budget * 0.2, "benefits": ["Logo on standees", "Standard booth", "Social media mention"]},
                    {"name": "Bronze", "amount": budget * 0.1, "benefits": ["Logo on website", "Brochure distribution"]},
                ],
                "audience_summary": f"Expected {context.audience_size or 'TBD'} attendees from {context.university_name}, {context.department}.",
                "email_drafts": [
                    {"industry": "tech", "subject_a": f"Partner with {context.society_name} for {context.event_title}", "subject_b": f"Sponsorship Opportunity: {context.event_title}", "body": "Dear [Company Name],\n\nWe are reaching out to explore a partnership opportunity... [AI unavailable — please customize this draft]"},
                ],
            }
