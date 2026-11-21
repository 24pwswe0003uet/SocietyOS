"""Policy extraction service — handles all 3 input modes from FR-002."""

import logging
from typing import Any

from app.services.ai.gemini import gemini_provider

logger = logging.getLogger("societyos.policy_service")

POLICY_EXTRACT_PROMPT = """You are SocietyOS AI, a university event policy analyst.

Analyze the following university document text and extract event-related policy information.

Document text:
\"\"\"
{text}
\"\"\"

Extract the following fields. Use null for any field not found in the document.
Only extract information that is explicitly stated or clearly implied.
Assign a confidence_score between 0.0 and 1.0 for the overall extraction quality.

Required JSON schema:
{{
  "approval_chain": {{
    "steps": [
      {{"order": 1, "authority": "name/title of approver", "role": "role_key"}}
    ]
  }},
  "lead_time_days": "integer - how many days before event must approval be submitted, or null",
  "required_documents": ["list of required documents for event approval"],
  "sponsorship_rules": "string describing sponsorship/funding rules, or null",
  "prohibitions": ["list of prohibited activities or restrictions"],
  "confidence_score": "float between 0.0 and 1.0",
  "source_references": ["page numbers or section names where info was found"]
}}
"""

POLICY_SCHEMA = """{
  "approval_chain": {"steps": [{"order": "int", "authority": "string", "role": "string"}]},
  "lead_time_days": "int|null",
  "required_documents": ["string"],
  "sponsorship_rules": "string|null",
  "prohibitions": ["string"],
  "confidence_score": "float",
  "source_references": ["string"]
}"""

QUESTIONNAIRE_PROMPT = """You are SocietyOS AI, a university event policy analyst.

Based on the following answers from a society member, infer reasonable policy information
for organizing events at their university. Be conservative — clearly label anything
that is inferred rather than confirmed.

Questionnaire answers:
1. Faculty Advisor: {faculty_advisor}
2. Department: {department}
3. Reports to: {reports_to}
4. Previous events experience: {previous_events}
5. Past rejections: {past_rejections}

Generate a reasonable policy data extraction. Set confidence_score lower (0.3-0.6)
since this is questionnaire-based inference, not document extraction.

Required JSON schema:
{{
  "approval_chain": {{
    "steps": [
      {{"order": 1, "authority": "name/title of approver", "role": "role_key"}}
    ]
  }},
  "lead_time_days": "integer estimate, or null",
  "required_documents": ["list of likely required documents"],
  "sponsorship_rules": "string with any inferred sponsorship rules, or null",
  "prohibitions": ["any known restrictions from past rejections"],
  "confidence_score": "float between 0.3 and 0.6 (questionnaire-based)",
  "source_references": ["questionnaire"]
}}
"""


def _clamp_confidence(raw: dict[str, Any]) -> dict[str, Any]:
    """Ensure confidence_score is between 0 and 1."""
    score = raw.get("confidence_score")
    if isinstance(score, (int, float)):
        raw["confidence_score"] = max(0.0, min(1.0, float(score)))
    else:
        raw["confidence_score"] = 0.5
    return raw


async def extract_policy_from_text(text: str) -> dict[str, Any]:
    """Mode 1 & 2: Extract policy data from document text via Gemini."""
    if len(text.strip()) < 50:
        return {
            "approval_chain": None,
            "lead_time_days": None,
            "required_documents": [],
            "sponsorship_rules": None,
            "prohibitions": [],
            "confidence_score": 0.1,
            "source_references": [],
        }

    # Truncate extremely long texts to fit within reasonable token limits
    max_chars = 500_000  # ~125K tokens
    truncated = text[:max_chars] if len(text) > max_chars else text

    prompt = POLICY_EXTRACT_PROMPT.format(text=truncated)

    try:
        raw = await gemini_provider.generate_structured(
            prompt=prompt,
            schema_description=POLICY_SCHEMA,
            max_tokens=4096,
        )
        return _clamp_confidence(raw)
    except Exception as e:
        logger.error("Policy extraction failed: %s", e)
        return {
            "approval_chain": None,
            "lead_time_days": None,
            "required_documents": [],
            "sponsorship_rules": None,
            "prohibitions": [],
            "confidence_score": 0.0,
            "source_references": [],
        }


async def extract_policy_from_questionnaire(
    faculty_advisor: str,
    department: str,
    reports_to: str,
    previous_events: str,
    past_rejections: str,
) -> dict[str, Any]:
    """Mode 3: Infer policy data from questionnaire answers."""
    prompt = QUESTIONNAIRE_PROMPT.format(
        faculty_advisor=faculty_advisor,
        department=department,
        reports_to=reports_to,
        previous_events=previous_events,
        past_rejections=past_rejections,
    )

    try:
        raw = await gemini_provider.generate_structured(
            prompt=prompt,
            schema_description=POLICY_SCHEMA,
            max_tokens=4096,
        )
        result = _clamp_confidence(raw)
        # Cap questionnaire confidence at 0.6
        result["confidence_score"] = min(0.6, result["confidence_score"])
        return result
    except Exception as e:
        logger.error("Questionnaire policy extraction failed: %s", e)
        # Fallback: build a basic chain from the answers
        return {
            "approval_chain": {
                "steps": [
                    {"order": 1, "authority": faculty_advisor, "role": "faculty_advisor"},
                    {"order": 2, "authority": f"HOD {department}", "role": "hod"},
                    {"order": 3, "authority": "Dean of Students", "role": "dean"},
                    {"order": 4, "authority": "Student Affairs Office", "role": "student_affairs"},
                ]
            },
            "lead_time_days": 14,
            "required_documents": ["Event proposal", "Budget plan", "Venue booking form"],
            "sponsorship_rules": None,
            "prohibitions": [],
            "confidence_score": 0.3,
            "source_references": ["questionnaire (fallback — AI unavailable)"],
        }
