"""Budget Planning Agent (FR-004)."""

import logging
from typing import Any

from app.services.agents.base import BaseAgent, EventContext
from app.services.ai.gemini import gemini_provider

logger = logging.getLogger("societyos.agents.budget")

PROMPT = """You are an expert university event budget planner for SocietyOS AI.

Create a detailed budget for the following event:

{context}

Generate a JSON object with this structure. All amounts should be in {currency}.
Budget categories: Venue, Catering, Marketing, Logistics, Security, Equipment, Contingency.
The contingency should be 10% of the subtotal (before contingency).

If a budget_target is specified, try to fit within it. Flag any category exceeding 40% of total.

{{
  "categories": [
    {{
      "name": "Venue",
      "items": [
        {{"description": "item name", "quantity": 1, "unit_cost": 50000, "total": 50000}}
      ],
      "subtotal": 50000
    }}
  ],
  "subtotal_before_contingency": 450000,
  "contingency_percent": 10,
  "contingency_amount": 45000,
  "grand_total": 495000,
  "currency": "{currency}",
  "warnings": ["list any warnings like categories exceeding 40%"]
}}

Include realistic cost estimates for Pakistan. Be specific with line items.
"""


class BudgetAgent(BaseAgent):
    agent_name = "budget"

    async def generate(self, context: EventContext) -> dict[str, Any]:
        prompt = PROMPT.format(context=context.full_prompt_context(), currency=context.currency)
        try:
            result = await gemini_provider.generate_structured(
                prompt=prompt,
                schema_description='{"categories":[{"name":"string","items":[{"description":"string","quantity":"int","unit_cost":"number","total":"number"}],"subtotal":"number"}],"subtotal_before_contingency":"number","contingency_percent":"int","contingency_amount":"number","grand_total":"number","currency":"string","warnings":["string"]}',
                max_tokens=4096,
            )
            return result
        except Exception as e:
            logger.error("Budget agent failed: %s", e)
            target = float(context.budget_target) if context.budget_target else 100000
            return {
                "categories": [
                    {"name": "Venue", "items": [{"description": "Venue rental", "quantity": 1, "unit_cost": target * 0.25, "total": target * 0.25}], "subtotal": target * 0.25},
                    {"name": "Catering", "items": [{"description": "Food & beverages", "quantity": 1, "unit_cost": target * 0.20, "total": target * 0.20}], "subtotal": target * 0.20},
                    {"name": "Marketing", "items": [{"description": "Marketing materials", "quantity": 1, "unit_cost": target * 0.10, "total": target * 0.10}], "subtotal": target * 0.10},
                    {"name": "Logistics", "items": [{"description": "Transport & logistics", "quantity": 1, "unit_cost": target * 0.10, "total": target * 0.10}], "subtotal": target * 0.10},
                    {"name": "Equipment", "items": [{"description": "AV equipment", "quantity": 1, "unit_cost": target * 0.15, "total": target * 0.15}], "subtotal": target * 0.15},
                    {"name": "Security", "items": [{"description": "Security staff", "quantity": 1, "unit_cost": target * 0.05, "total": target * 0.05}], "subtotal": target * 0.05},
                ],
                "subtotal_before_contingency": target * 0.85,
                "contingency_percent": 10,
                "contingency_amount": target * 0.085,
                "grand_total": target * 0.935,
                "currency": context.currency,
                "warnings": ["Budget generated from fallback estimates — AI unavailable"],
            }
